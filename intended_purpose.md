# Intended Purpose

* **Structure and Function of the device**
The purpose of the tool is to help clinicians identify the relative risks of bleeding outcomes and ischaemic outcomes for patients presenting with acute coronary syndromes (ACS), for the purpose of choosing between different therapy options.
Currently stratified risk scores do exist but, annocdotelly, are not routinely used in the evaluation of patients initiated on anti-coauglation.
Our device would allow for existing risk scores to be used within existing workflows and for the additional use of a machine learning trained device to risk stratify patients. 

For example, if a patient is identified as being at a high risk of bleeding through the use of the tool then the clinician could use this information to choose a less aggressive blood thinning therapy option.

In addition to providing risks on request, the tool should also notify relevant health care professionals if the risks change enough to warrant a change in therapy at any point in a monitoring period (this may be difficult as we would have to set parameters for change rather than parameters to flag high risk).

The tool should be easy enough to use that it can be incorporated into routine clinical practice. This includes not requiring the user to source a large quantity of information required to produce the relative risks.
The tool should operate with data that is readily available for an inpatient.


* **Indications for use** *

* **Who will use the tool**: clinicians or other health care professionals involved in the assessment of what blood thinning therapy to prescribe to a patient. 
* **When will the tool be used**: when a patient presents with an ACS, and blood thinning therapy is indicated. In addition, any time the risks change and a relevant health-care professional is notified in the monitoring period. It is ecpected that a healthcare professional would be able to requet an automated risk score when requesting other laboratory investigations.
* **What output will the tool give**: any output that indicates a patient's relative bleeding/further ischaemia risk. This could be probabilities from a model, or a simple high/low indicator based on a simple consensus-based calculation. The output from the tool will be decided by choosing from a list of alternative solutions according to (in order of importance):
    * which one best meets the intended purpose
    * which one is simplest to implement
* **What form will the tool take**: The tool will be constructed to operate within the existing IT infrastructure. For example the ICE lobaoratory request and result system. This would allow for use within existing workflows. Further, patient identifiable informaton would be suitably protected. In the event of ICE not being available, then a seperate bespoke system may be required.

* **what clinical evidence is required to demonstrate the device meets the specifics of the intended prupose?** Pre-deployment a review with local and external data would be required. Post deployment an audit of the device risk scores with a selected sample of case reviews to demonstrate whether the scores impact patient management. A retro-spective analysis of the number of patients being admitted to hospital post PCI with haemorrhage.
 
* **Reasonably forseeable misuse case**: The risk score could be used on the wrong patient group. 