# Alternative Forms of the Tool

This file describes alternative types of tool that might satisfy the intended purpose. 

## New stand-alone software

The tool will be a desktop application (for Windows and Mac), and a mobile phone application (for Android and iOS). The desktop application will be installed in relevant clinical locations (e.g. the CathLab, on the ward computer trolleys, etc.). The mobile phone application will be installable by any clinician involved in the patient's care.

The calculations themselves will take place in a server, installed on the hospital site, which will be able to source some information automatically from electronic hospital systems, and source some information from the frontend desktop/mobile applications.

Clinicians can trigger a risk calculation from the desktop/mobile application. In addition, clinicians who have opted-in to notifications about a particular patient will receive push notifications if the risk for that patient changes. The server will regularly (multiple times per day) poll its information sources, and recalculate patient risk, to check if this notification should be sent.

### Advantages

* Flexibility of implementation (what can be included/how the tool can be designed); might be better tailored to intended purpose
* Automatic interface to hospital systems may be able to reduce manual information input as much as possible.

### Disadvantages

* Complexity of implementation (depending how much is designed from scratch).
* Complexity of interfacing with existing hospital systems.

## Integrated into routine lab tests

TODO