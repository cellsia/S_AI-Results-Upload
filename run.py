import logging
import sys
import json

import cytomine

from cytomine.models import AnnotationCollection, Annotation, Job, JobData
from cytomine.models.software import JobDataCollection
from shapely.geometry import box

__version__ = "1.0.0"


def _generate_rectangles(detections):
    
    rectangles = []

    for detection in detections['rectangles']:
        logging.info(f"X0 {detection['x0']}  Y0 {detection['y0']}  X1 {detection['x1']}  Y1{detection['y1']}")
        rectangles.append(box(detection['x0'],detection['y0'],detection['x1'],detection['y1']))
    
    return rectangles


def run(cyto_job, parameters):
    logging.info("----- IA results uploader v%s -----", __version__)

    job = cyto_job.job
    project = cyto_job.project
    image = parameters.cytomine_image
    term = parameters.cytomine_id_term

    job_data_collection = JobDataCollection().fetch_with_filter('job', job.id)
    job_data = next((j for j in job_data_collection if j.key == 'detections'), None)
    if not job_data:
        job.update(progress=100, status=Job.FAILED, statusComment="Detections cannot be found")
        sys.exit()

    filename = 'detections-' + str(job.id) + '.json'
    if not JobData().fetch(job_data.id).download(filename):
        job.update(progress=100, status=Job.FAILED, statusComment="Detections cannot be found")
        sys.exit()

    with open(filename) as json_file:
        detections = json.load(json_file)


    # Load annotations from provided JSON
    rectangles = _generate_rectangles(detections)

    progress = 10
    job.update(progress=progress, status=Job.RUNNING, statusComment=f"Uploading detections to image {image} (Project: {project.id}) with term {term}")

    # Upload annotations to server
    delta = 85 / len(rectangles)
    new_annotations = AnnotationCollection()
    for rectangle in rectangles:
        new_annotations.append(Annotation(location=rectangle.wkt, id_image=image, id_term=[term]))
        progress += delta
        job.update(progress=int(progress), status=Job.RUNNING)

    new_annotations.save()
    progress = 100
    job.update(progress=progress, status=Job.TERMINATED, statusComment="All annotations have been uploaded")


if __name__ == "__main__":
    logging.debug("Command: %s", sys.argv)

    with cytomine.CytomineJob.from_cli(sys.argv) as cyto_job:
        run(cyto_job, cyto_job.parameters)

        