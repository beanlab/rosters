
Can you please come up with a way to display the results as presented in C:\Users\rebek\School\F26\CS401R_F26\experiments\jev-pre-function-quality-review-experiment\results\1-parse-repo\scores.yaml ?

I want a single html file that can be generated from the results. I want to be able to share a single file. 

I want to easily be able to see the hotspots where there are issues, and the overall scores.

I want to have a layered approach, where if I want to see more about a particular file or function,
then I can click on it. 

I also want to be able to see a heatmap of the files/directories overall, and then have an option to toggle per category. 
I want to be able to easily see that a particular file/directory is much worse or much better than what it compared with. 

Ensure you follow best programming practices. Make this very easy to change if I change the scoring metrics. DRY. SRP. Avoid any accidental complexity. 

Make it a feature, that one file can represent multiple score files at the same time. It can show the overall score for each of the score files/projects with its name, and then if someone is curious, they can click on that overall score, and then everything else I previously described is displayed. 

You will know you are done when I have a program where I can input a results file(s), and get back a static HTML page that I can interact with easily. 

