import logging
import sys
import json

import cytomine

from cytomine.models import AnnotationCollection, Annotation, Job
from shapely.geometry import box

__version__ = "0.0.13"


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
    json_string = parameters.detections

    job.update(progress=0, status=Job.RUNNING, statusComment=f"Parsing detections {json_string}")

    logging.info("JSON: %s", json_string)
    print(json_string)

    # Load annotations from provided JSON
    detections = json.loads(json_string)
    rectangles = _generate_rectangles(detections)

    job.update(progress=10, status=Job.RUNNING, statusComment=f"Uploading detections to image {image} (Project: {project.id}) with term {term}")

    # Upload annotations to server
    new_annotations = AnnotationCollection()
    for rectangle in rectangles:
        new_annotations.append(Annotation(location=rectangle.wkt, id_image=image, id_term=[term]))
    new_annotations.save()

    job.update(progress=100, status=Job.TERMINATED, statusComment="All annotations have been uploaded")


if __name__ == "__main__":
    logging.debug("Command: %s", sys.argv)

    with cytomine.CytomineJob.from_cli(sys.argv) as cyto_job:
        run(cyto_job, cyto_job.parameters)

        