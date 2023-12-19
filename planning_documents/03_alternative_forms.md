# Alternative Forms of the Tool

This file describes alternative types of tool that might satisfy the intended purpose. 

## Description of the system

The tool comprises a risk score calculation, which takes patient information as inputs and produces a bleeding and ischaemia risk as output (see [Alternative Risk Scores](alternative_risk_scores.md) for more information). It can be considered as a black box from the point of view of the rest of the system.

The rest of the system is software or processes that enable the risk score to be calculated and brought to clinicians in a way that meets the intended purpose. The section below describes alternative formats for this system.

## Alternative Systems List

### Integrated into routine lab tests

The tool will be constructed to operate within the existing IT infrastructure, using the ICE laboratory request and result system. This would allow for use within existing workflows. Further, patient identifiable information would be suitably protected.

Questions (might be naive):

* How often are new tests integrated into the lab? Is there a system/policy for doing it?
* Is there any precedent for lab tests which are not "proper" lab tests like bloods etc. -- i.e. anything similar to a risk score?
* How is the output of lab tests presented to clinicians/is there flexibility in how the system (ICE?) presents results
* Do any current lab tests require collection of patient information (like age, gender, etc.) as part of calculating the results?
* Is there any equivalent of a "standing order" for a lab test (i.e. do this test for this patient every week), or are all tests triggered by clinician requests?

#### Advantages

* More of the work is integrated into routine lab tests, and could be taken away from front-line clinicians.
* More manual data could be collected if this was incorporated as a part of a standard process, as for a laboratory test.

#### Disadvantages

* May be difficult to trigger ongoing monitoring of patient risk (who would trigger the re-evaluation?)

### New stand-alone software

The tool will be a desktop application (for Windows and Mac), and a mobile phone application (for Android and iOS). The desktop application will be installed in relevant clinical locations (e.g. the CathLab, on the ward computer trolleys, etc.). The mobile phone application will be installable by any clinician involved in the patient's care.

The calculations themselves will take place in a server, installed on the hospital site, which will be able to source some information automatically from electronic hospital systems, and source some information from the frontend desktop/mobile applications.

Clinicians can trigger a risk calculation from the desktop/mobile application. In addition, clinicians who have opted-in to notifications about a particular patient will receive push notifications if the risk for that patient changes. The server will regularly (multiple times per day) poll its information sources, and recalculate patient risk, to check if this notification should be sent.

#### Advantages

* Flexibility of implementation (what can be included/how the tool can be designed); might be better tailored to intended purpose
* Automatic interface to hospital systems may be able to reduce manual information input as much as possible.

#### Disadvantages

* Complexity of implementation (depending how much is designed from scratch).
* Complexity of interfacing with existing hospital systems.

