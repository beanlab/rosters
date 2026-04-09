## Intent

The application design should clearly document the **user** and **operations** interfaces
of the application.

These two interfaces represent how the application interacts with the real world. 

The **user** interface embodies what the product looks like and how it acts. 
It describes what the application does and how users interact with it.
Tests are designed to verify that the application conforms to the expectations 
of the user interface.

The **operations** interface describes how developers and devops interact with the application.
This includes details such as how the application is configured, runtime dependencies, etc.
While not visible to the user, these details are important to how the software product 
interacts with the real world; changes to this interface require corresponding changes outside.

Implementation details should not be included in the application design document.
If a change to the code won't affect how the software is operated (by users or operations) 
or how the software makes changes in the real world, then it is an implementation detail.

