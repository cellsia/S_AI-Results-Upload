import logging
import sys
import json

import cytomine

from cytomine.models import AnnotationCollection, Annotation, Job
from shapely.geometry import box

__version__ = "0.0.1"


def _generate_rectangles(detections):
    
    rectangles = []

    for detection in detections:
        rectangles.append(box(detection[0],detection[1],detection[2],detection[3]))
    
    return rectangles


def run(cyto_job, parameters):
    logging.info("----- IA results uploader v%s -----", __version__)

    job = cyto_job.job
    project_id = cyto_job.project
    image = parameters.image
    term = parameters.term
    json_string = parameters.detections

    job.update(progress=0, status=Job.RUNNING, statusComment=f"Converting annotations from project {project_id}")

    # Load annotations from provided JSON
    detections = json.load(json_string)
    rectangles = _generate_rectangles(detections)

    # Upload annotations to server
    new_annotations = AnnotationCollection()
    for rectangle in rectangles:
        new_annotations.append(Annotation(rectangle.wkt, image.id, term.id, project_id))
    new_annotations.save(chunk = None)

    job.update(progress=100, status=Job.TERMINATED, statusComment="All annotations have been uploaded")


if __name__ == "__main__":
    logging.debug("Command: %s", sys.argv)

    with cytomine.CytomineJob.from_cli(sys.argv) as cyto_job:
        run(cyto_job, cyto_job.parameters)

        