### How To Run it

This bot is running on cd-go machine (linux)
```bash
sudo add-apt-repository ppa:fkrull/deadsnakes # If it is not previously there  
sudo apt-get update  
sudo apt-get install python3.6 python3-pip -y  
sudo python3.6 -m pip install -r requirements.txt  
screen -S bot  
python3.5 run.py  
```
- use `[Ctrl+a+d]`to detach from the console  
- use `screen -R bot` -> reattach

The bot ~~has a global try catch~~ is robust enough to keep on running after an exception.  
 _TODO Make it run on docker, the restart policy is cool_

###Go-Cd integration pipeline notifier  
#####Logic overview

The purpose of this tool is to improve visualization on the status of the integration pipeline on cd-go:8134 which 
usually stays broken for days.  
The tool will send a slack notification _every time a new run breaks the pipeline*_, as well as a daily summary that
 as a reminder of the failed tests left running. Each message will include some basic information about the failed tests.

The tool is configurable up to a certain extent by changing the values provided in [app.cfg](#Config file)

```
A typical process flow of the application would be:
1. Request to Cd-Go to obtain details of the pipeline last run
2. Pull Cd-Go tests result HTML and parse it into an in memory object
3. Process test result object (obtain metrics, stored in a class)
4. Load previous data from storage file
5. Detect modifications on the results, flag item that will appear in the notification
6. Save current status to file
7. Send slack notification
```

\* After some testing, the bot is quite noisy because of brittle test breaking each other run, until this issue is 
addressed, the bot will only send a summary notification @6, 12, 18.

#####Backup file

The current status of the run is saved to 'notifications.bak', which has the following structure:
  
- First line: Datetime of the last successful daily notification   
- Each subsequent line is a text representation of the class FailureEvent.

All dates need to be provided in [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) format.

#####Config file

It is divided in sections:  
1. AppConfig: Related to the application, how often it runs, how often it polls CD-Go, target file names etc
  + PollingFreq: seconds between each poll to CD-Go  
  + CronSchedule: Summary notification schedule in unix [crontab](https://en.wikipedia.org/wiki/Cron)style
  + SlackChannel: name of the channel the notifications are posted. Default: webhooktest (private)
  + PipelineName, StageName, JobName: Details for the stage to be watched.
  + BackOffPeriod: Legacy code for the summary notifications, but still functional if the cron schedule is not specified
  or it fails to be parsed  
  + StorageFileName: Target file used as a database/backup, explanation about the expected format [here](#Backup file  )
2. Credentials: all the credentials required for the notification tools used (only slack at the moment)
  + CD-Go credential is a GRN account with permissions limited to read-only on CD-Go.  
  + Account name is "cd-service"
3. ConnectionStrings: for any database/api  
  + The slack webhook can be generated from the slack website