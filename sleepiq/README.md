# SleepIQ Integration with LAMBDA and Alexa

About Lambda Functions
----------------------
AWS Lambda Functions are a method of executing serverless code on demand via invocation methods such as REST calls or Alexa Skills.

Preparing your package for upload
---------------------------------
This lamda function depends on the sleepyq module developed by Josh Nichols:
 - Josh Nichols
 - GitHub: https://github.com/technicalpickles 

This module is not available by default, so we need to create a bundle that
contains it as part of completing the lambda integration. Luckily, it isn't
that hard to do, and even Google helped me do it thanks to:

https://medium.com/@manivannan_data/import-custom-python-packages-on-aws-lambda-function-5fbac36b40f8

Using the above as a guide, I'm summarized the relevant steps below:
1. Install Python 3.7 if you haven't already

`sudo pip install python3.7`

note: AWS as of this writing supports 3.7. This may change over time, so if it
      does, make sure to match their requirements.

2. Install virtualenv on your system (if you don't have it already)

`sudo pip3 install virtualenv`

3. Create your virtual environment

`virtualenv -p /usr/bin/python3.7 sleepnumber`

note: based on your distribution, your path above may be different
      (e.g. /usr/local/bin/python3.7)

4. Activate your virtual environment

`source sleepnumber/bin/activate`

5. Install packages into your virtual environment

`pip3 install sleepyq`

6. Copy lambda function to your environment's site-packages folder

`cp {path_to}/lambda_function.py sleepnumber/lib/python3.7/site-packages/`

7. Zip up everything inside of site-packages (within your venv!)

```
cd sleepnumber/lib/python3.7/site-packages
zip -r9 sleep_number_lambda.zip *
```

8. Follow steps in the next section to install and activate your function.

Integrating sleepiq lambda in your environment
----------------------------------------------
1. Log into your AWS CONSOLE (aws.amazon.com).
   - If you're not logged in, you should see "Sign In to the Console" on the 
     upper right.
   - If this is your very first time, you may have signing up to do.
2. Either search for or select 'Lambda' from the Compute services list.
3. In the functions page, click "Create function".
4. Choose "Author from scratch (default)"
5. Give it a name (e.g. SleepNumber)
6. Pick the Python 3.7 runtime.
7. Click "Create function"
9. Scroll down to Function code and select "Upload a .zip file" from the
   "Code entry type" dropdown.
10. Click Upload and select the .zip file you added earlier.
11. Click Save (but you're not ready to test it yet!)

Create your user/pass env variables
-----------------------------------
So that your code doesn't have to have your username and password hardcoded, we
use Amazon's environment variables. The variables can also be encrypted to
ensure nobody will see your password. It's pretty cool.

1. Create a key SNUSER and enter your sleepiq username in for 'Value'
2. Create a key SNPASS and enter your sleepiq password in for 'Value'
  Note: The LAMBDA code's comments mention this too, but you don't HAVE to
        encrypt your USER/PASS. It is a more complex setup, and it costs
        you small sums of money to do so depending on how often the service 
        is used due to the NAT Gateway and Key Management Service. If you
        don't want to encrypt, skip 3-5 and in the code follow the instructions.
3. Check the 'Enable helpers for encrypting in transit' box.
 note: if you haven't configured KMS before, you'll be told you have to. Take
       care of that in a new window and come back to your lambda function to
       complete your ENV variable setup.
4. Once you have your KMS key set up, you can select it in the dropdown.
5. Use (default) aws/lambda for KMS key to encrypt at rest.
6. Click Save.

Test your function
------------------
Included in the tests/ folder are a few .json files you can use to test your
function. Simply go to the top of the function page and click on the dropdown
next to 'Test' and choose "Configure test events".  You can copy the .json
in for each of these tests. All should pass and you should see the response
output in the green box. If things don't pass, you missed a step and the
error may help indicate where.


Creating your Alexa Skill and linking it to your lambda function
----------------------------------------------------------------
Now that we know that the lambda function is working by testing it, it is time
to create the Alexa skill that will complete the functionality. 

1. Go to developer.amazon.com
2. Click on Alexa, and navigate to create a skill.
3. Once you get to the alexa developer console, click "Create Skill"
4. Enter a name for the skill (e.g. SleepNumber)
5. Choose Custom model and Provision your own for hosting
6. Click 'Create skill'
7. Choose 'Start from scratch'
8. Click on Invocation and enter "sleep number" - include the space.
     - this is the name you use when you say "Alexa, ask sleep number..."
9. Click on JSON Editor lower down on the left side. Copy the contents of
   skill.json from the alexa/sleepiq/ into the JSON editor.
10. Click 'Save Model', then 'Build Model'. This should build without issue.
11. Click on Endpoint on the left side.
12. Choose the "AWS Lambda ARN" radio button.
13. Save off the Skill ID in a notepad somewhere. You'll need it back in your
    Lambda function soon.
14. In the Default Region field, you need to enter in the ARN for your Lambda
    function. You can find this at the top of the page in your Lambda function.
    It should start with "ARN - arn:aws.lambda:XXXXXXXXXXXXX". Copy and paste
    that entire string in the box in your skill.
15. Click 'Save Endpoints'.
16. Head back to your Lambda function. Be sure to have copied your Skill ID
 (back in your Lambda function...)
17. In new dialog, once created, click the "+ Add trigger" button and select
   Alexa Skills Kit
18. In the Skill ID field, copy the Skill ID you copied earlier, then click
    Add.

Try out your new skill and control your bed with your voice!
------------------------------------------------------------
Try, "Alexa, ask sleep number to fill bed."
