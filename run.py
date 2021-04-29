import logging
import sys
import json

import cytomine

from cytomine.models import AnnotationCollection, Annotation, Job, JobData, AnnotationTerm
from cytomine.models.software import JobDataCollection
from shapely.geometry import box, Point, MultiPoint, Polygon


__version__ = "1.1.6"


def _generate_rectangles(detections: dict) -> list: 
    
    rectangles = []

    for detection in detections['rectangles']:
        #logging.info(f"X0 {detection['x0']}  Y0 {detection['y0']}  X1 {detection['x1']}  Y1 {detection['y1']}")
        rectangles.append(box(detection['x0'],detection['y0'],detection['x1'],detection['y1']))
    
    return rectangles


def _generate_multipoints(detections: list) -> MultiPoint:

    points = []
    for detection in detections:
        points.append((detection['x'], detection['y']))

    return MultiPoint(points=points)


def _generate_polygons(detections: dict) -> list:
    polygons = []

    for detection in detections['polygons']:
        polygon_points = []
        for point in detection:
            polygon_points.append((int(point['x']), int(point['y'])))
        
        polygons.append(Polygon(polygon_points))

    return polygons


def _load_rectangles(job: Job, image_id: str, term: int, detections: dict) -> None:

    progress = 10
    job.update(progress=progress, status=Job.RUNNING, statusComment=f"Uploading detections of type rectangles to image {image_id} with terms {term}")

    rectangles = _generate_rectangles(detections)

    # Upload annotations to server
    delta = 85 / len(rectangles)
    annotations = AnnotationCollection()
    for rectangle in rectangles:
        annotations.append(Annotation(location=rectangle.wkt, id_image=image_id, id_terms=[term]))
        progress += delta
        job.update(progress=int(progress), status=Job.RUNNING)

    annotations.save()
    progress = 100
    job.update(progress=progress, status=Job.TERMINATED, statusComment="All detections have been uploaded")


def _load_multi_class_points(job: Job) -> None:

    progress = 100
    job.update(progress=progress, status=Job.TERMINATED, statusComment="Job finished")


def _load_polygons(job: Job, image_id: str, term: int, detections: dict) -> None:

    progress = 10
    job.update(progress=progress, status=Job.RUNNING, statusComment=f"Uploading detections of type polygons to image {image_id} with terms {term}")

    polygons = _generate_polygons(detections)

    delta = 85 / len(polygons)
    annotations = AnnotationCollection()
    for polygon in polygons:
        annotations.append(Annotation(location=polygon.wkt, id_image=image_id, id_terms=[term]))
        progress += delta
        job.update(progress=int(progress), status=Job.RUNNING)

    annotations.save()
    progress = 100
    job.update(progress=progress, status=Job.TERMINATED, statusComment="All detections have been uploaded")


def run(cyto_job, parameters):
    logging.info("----- IA results uploader v%s -----", __version__)

    job = cyto_job.job
    #project = cyto_job.project
    image = parameters.cytomine_image
    terms_str = parameters.cytomine_id_term
    if terms_str == "[]":
        terms = []
    else:
        terms = terms_str.replace(' ', '').strip('[] ').split(',')
        terms = list(map(int, terms))
    detections_type = parameters.type_of_detections

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

    if detections_type == 'rectangles':
        _load_rectangles(job, image, terms[0], detections)
    elif detections_type == 'multi-class-points':
        _load_multi_class_points(job)
    elif detections_type == 'polygons':
        _load_polygons(job, image, terms[0], detections)


if __name__ == "__main__":
    logging.debug("Command: %s", sys.argv)

    with cytomine.CytomineJob.from_cli(sys.argv) as cyto_job:
        run(cyto_job, cyto_job.parameters)

        