import sys
from messageGroup import messageGroup
from patchListenerJob import check_for_patch

JOB_FAILED_STATUS = "Job Failed"
JOB_SUCCEEDED_STATUS = "Job Succeeded"
JOB_SKIPPED_STATUS = "Job Skipped"

# Arg 1 : Riot Api Key
# Arg 2 : Discord Bot Api Key
# Arg 3 : (Optional) Debug Flag
def main():
    if len(sys.argv) > 2:
        riot_api_key = sys.argv[1]
        discord_bot_api_key = sys.argv[2]
        
        debugFlag = False
        if len(sys.argv) > 3:
            debugFlag = sys.argv[3] == "debug"

        try:
            jobStatusWrapper(messageGroup.__name__, messageGroup(riot_api_key, discord_bot_api_key, debugFlag))
        except:
            jobStatusWrapper(messageGroup.__name__, 0)            
            
        try:
            jobStatusWrapper(check_for_patch.__name__, check_for_patch(riot_api_key, discord_bot_api_key, debugFlag))
        except:
            jobStatusWrapper(check_for_patch.__name__, 0)
    else:
        print("No Riot Api Key or Discord Api Key Provided")
        
def jobStatusWrapper(jobName, jobResult):
    match jobResult:
        case -1:
            print(f"{jobName} {JOB_SKIPPED_STATUS}")
        case 0:
            print(f"{jobName} {JOB_FAILED_STATUS}")
        case 1:
            print(f"{jobName} {JOB_SUCCEEDED_STATUS}")

if __name__ == "__main__":
    main()