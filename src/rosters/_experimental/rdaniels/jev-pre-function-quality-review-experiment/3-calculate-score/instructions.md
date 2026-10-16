

Can you please create a **minimum viable product** for creating a score from the output of a previous program? 

This is the input that you can expect things to be in when it is called: 
C:\Users\rebek\School\F26\CS401R_F26\experiments\jev-pre-function-quality-review-experiment\results\1-parse-repo\function-review.yaml

For the output, ensure that it is readable and parsable. Another program will be reading your results afterwards. Using yaml or markdowndata for the output. 

What is being scored should be apparent in the file. 

I want to be able to specify a threshold of whether it meets the critieria. 
For now, use a threshold of .85 as default -- but allow it to be changed by the user by cli arguments on the command line. 

I want a couple different scores: 
- Basic Score:  
    - Basic score: number of good things / total number of things. If its a good thing it meets the threshold, then add a point. (ie if >.85 for yes on a positive thing or if >.85 for a no on a negative thing). I'm going to call this the "basic score"
    - Basic score for each file -- instead of all the functions, I want a score per file.
    - Basic score for each function -- record each individual function score.
    - Basic score for each module
    - Basic score overall
- Weighted score
    - based on the depth of a function, I'm using a heurstic to say how important it is. So the deeper a function is, the less important it is. However, if it is a higher level function, and less nested, then it is more important. the middle functions are also important. 
        So the score I want is to have each individual function's basic score be weighted by the nested depth. 
        For example, if a function is at the bottom of the call stack, the depth from the bottom is 1. It should have the lowest weight 
        If a function is in the middle, then it should have medium weight. 
        If a function is at the very top, and has lots of functions that it is calling, it should have higher weight. 

    - I want this weighted score for each file (ie recalculate it as a weighted score)
    - I want this weighted score for the files in each module
    - I want this weight score for the program overall 

I also want the basic and weighted scores for each of the categories individually -- for function, file, module and overall levels. 
For example, there is a category in Jev's judgments called "readability_and_naming". I want to see the readability_and_naming on its own. 

If anything is unclear, raise and ask questions. 

The output should be parsable by another program and easy to read by a person. Use yaml or the python package markdowndata. 

Ensure you follow best programming practices. Make this very easy to change if I change the scoring metrics. DRY. SRP. Avoid any accidental complexity. 

You will know you are finished when I have a program that I can run that takes the output of jev's judgments and outputs a file with all the scores I specified above. 

