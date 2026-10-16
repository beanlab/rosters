
Read this: https://github.com/paramjeetn/jev-cookbook/blob/master/THEORY.md#the-theory-of-jev-a-staff-engineers-guide-to-system-one-ai 

Then read this: https://github.com/typesafe-ai/skills/blob/main/skills/typesafe-ai/SKILL.md

Follow the instructions provided .

Can you please create a **minimum viable product** for going through each of the functions and judging them with jev on the questions in code checks? 

Avoid introducing accidental complexity. Follow best coding practices so it will be easy for me to change in the future. 

Can you please save the code checks in such a way that it is easy to understand and for me to change in the future? Please use yaml or markdowndata. 
Please mark them as positive and negative questions. (ie if the answer is yes it is a good thing, versus if the answer is no it is a bad thing)
and still keep them in generalized groups. 

Let's use nouls. Please record the response to each question so I can later reference and parse it. 

This is the input that you can expect things to be in when it is called: 
C:\Users\rebek\School\F26\CS401R_F26\experiments\jev-pre-function-quality-review-experiment\results\1-parse-repo\parsed.json

For the output, ensure that it is readable and parsable. Another program will be reading your results afterwards. Using yaml or markdowndata for the output. 

Before running the jev calls, please determine how much it would cost to run jev -- without actually calling jev. 
You may use a basic hueristic to determine how much it costs to call jev. 
Get the user's approval before running the program after displaying how much it will cost. 

At the end, please print the cost of running the program, and the time it took. 

You will know when you are done when there is a working program that takes in the provided json input 
and then produces a file with jev output on the input using the code checks given, 
with a user verification that they are okay with the cost. 

