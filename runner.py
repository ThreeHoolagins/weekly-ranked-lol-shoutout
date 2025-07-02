import sys
import logging

from datetime import datetime
from messageGroup import messageGroup
from patchListenerJob import PatchNotPostedException, check_for_patch

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
    if len(sys.argv) > 2:
        riot_api_key = sys.argv[1]
        discord_bot_api_key = sys.argv[2]
        
        debugFlag = False
        if len(sys.argv) > 3:
            debugFlag = sys.argv[3] == "debug"
            LOG.info("\n\nDebug run started at %s\n\n", datetime.now().strftime("%Y/%m/%d %I:%M %p"))

        try:
            jobStatusWrapper(messageGroup.__name__, messageGroup(riot_api_key, discord_bot_api_key, debugFlag))
        except:
            jobStatusWrapper(messageGroup.__name__, 0)
            
        try:
            jobStatusWrapper(check_for_patch.__name__, check_for_patch(riot_api_key, discord_bot_api_key, debugFlag))
        except PatchNotPostedException as e:
            print("Patch not found")
            jobStatusWrapper(check_for_patch.__name__, -1)
        except Exception as e:
            print(e)
            jobStatusWrapper(check_for_patch.__name__, 0)
    else:
        LOG.error("No Riot Api Key or Discord Api Key Provided")
        
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