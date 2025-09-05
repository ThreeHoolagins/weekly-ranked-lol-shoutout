import sys
import logging

from datetime import datetime
import traceback
from data import DISCORD_BOT_KEY, RIOT_API_KEY
from emailPage import PageError
from messageGroup import messageGroup
from patchListenerJob import PatchNotPostedException, check_for_patch
from skinDataJob import skinLineDataJob

JOB_FAILED_STATUS = "Job Failed"
JOB_SUCCEEDED_STATUS = "Job Succeeded"
JOB_SKIPPED_STATUS = "Job Skipped"

# Arg 1 : Riot Api Key
# Arg 2 : Discord Bot Api Key
# Arg 3 : (Optional) Debug Flag
def main():
    LOG = logging.getLogger("pipeline")

    logging.basicConfig(filename=f'logs/runs{datetime.now().strftime("%Y-%m-%d")}.log', 
        filemode='a',
        encoding='utf-8', 
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
        datefmt='%m/%d/%Y %I:%M:%S %p')
        
    debugFlag = False
    if len(sys.argv) > 1:
        debugFlag = sys.argv[1] == "debug"
        LOG.info("\n\nDebug run started at %s\n\n", datetime.now().strftime("%Y/%m/%d %I:%M %p"))

    try:
        jobStatusWrapper(messageGroup.__name__, messageGroup(RIOT_API_KEY, DISCORD_BOT_KEY, debugFlag))
    except:
        LOG.error(traceback.format_exc())
        PageError(traceback.format_exc())
        jobStatusWrapper(messageGroup.__name__, 0)
        
    try:
        jobStatusWrapper(check_for_patch.__name__, check_for_patch(RIOT_API_KEY, DISCORD_BOT_KEY, debugFlag))
    except PatchNotPostedException as e:
        LOG.info("Patch Not Found")
        jobStatusWrapper(check_for_patch.__name__, -1)
    except Exception as e:
        LOG.error(traceback.format_exc())
        PageError(traceback.format_exc())
        jobStatusWrapper(check_for_patch.__name__, 0)
        
    try:
        jobStatusWrapper(skinLineDataJob.__name__, skinLineDataJob())
    except:
        LOG.error(traceback.format_exc())
        PageError(traceback.format_exc())
        jobStatusWrapper(skinLineDataJob.__name__, 0)
        
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