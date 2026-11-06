import logging
import sys
import traceback
from datetime import datetime

from config import runtime
from emailPage import PageError
from messageGroup import messageGroup
from patchListenerJob import PatchNotPostedException, checkForPatch

JOB_FAILED_STATUS = "Job Failed"
JOB_SUCCEEDED_STATUS = "Job Succeeded"
JOB_SKIPPED_STATUS = "Job Skipped"


# Arg 1 : (Optional) "debug" to run in debug mode
def main():
    LOG = logging.getLogger("pipeline")

    logging.basicConfig(
        filename=f"data/logs/runs{datetime.now().astimezone().strftime('%Y-%m-%d')}.log",
        filemode="a",
        encoding="utf-8",
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%m/%d/%Y %I:%M:%S %p",
    )

    runtime.DEBUG = len(sys.argv) > 1 and sys.argv[1] == "debug"
    if runtime.DEBUG:
        LOG.info("\n\nDebug run started at %s\n\n", datetime.now().astimezone().strftime("%Y/%m/%d %I:%M %p"))

    try:
        jobStatusWrapper(messageGroup.__name__, messageGroup())
    except Exception:
        LOG.error(traceback.format_exc())
        PageError(traceback.format_exc())
        jobStatusWrapper(messageGroup.__name__, 0)

    try:
        jobStatusWrapper(checkForPatch.__name__, checkForPatch())
    except PatchNotPostedException:
        LOG.info("Patch Not Found")
        jobStatusWrapper(checkForPatch.__name__, -1)
    except Exception:
        LOG.error(traceback.format_exc())
        PageError(traceback.format_exc())
        jobStatusWrapper(checkForPatch.__name__, 0)


def jobStatusWrapper(jobName, jobResult):
    LOG = logging.getLogger("pipeline")
    match jobResult:
        case -1:
            LOG.info(f"{jobName} {JOB_SKIPPED_STATUS}")
        case 0:
            LOG.error(f"{jobName} {JOB_FAILED_STATUS}")
        case 1:
            LOG.info(f"{jobName} {JOB_SUCCEEDED_STATUS}")


if __name__ == "__main__":
    main()
