# Table of Contents
1. [Solution Summary](README.md#solution-summary)
2. [Batchlog processing and network starting state](README.md#Batchlog-processing-and-network-starting-state)
3. [Streamlog processing and anomaly detection](README.md#Streamlog-processing-and-anomaly-detection)
4. [Dependencies](README.md#Dependencies)
5. [Testing and test data notes](README.md#Testing-and-test-data-notes)
6. [Running the script] (README.md#running-the-script)
7. [Additional features] (README.md#additional-features)
8. [Assignment Original README] (README.md#Assignment-original-README)

#Solution Summary

In the challenge initial README, the business case and background of the 
problem are discussed. In this document, only the solution itself and the way it
works will be discussed.

within the project folder there will be an src folder containing the process_log 
script
it is named:
    ./src/process_log.py
    
input files are expected in the input_log folder and are two files, batch log
 and stream log: 
    ./input_log/batch_log.json
    ./input_log/stream_log.json
    
output files will be placed in the output_log folder and is one file, flagged purchases
    ./output_log/flagged_purchases.json
    
Batch log file layout: 

within the batch log it is expected that the first row will not contain actual 
data, but will contain the values for the two variables D and T, to be used 
through the execution of the data processing. 
 D = the number of degrees that define a user's social network. 
 T = the number of historic purchases to consider in the anomaly detection 
     algorithm (excluding the usuers own purchases)


#Batchlog processing and network starting state 



the building of the social network graph, and all graph functions used within 
the script use the Python library networkx. networkx allows you to build connected
node and edge graphs using lists of edges. when a new edge is added, the nodes on
either end are added if they do not already exist. therefore to construct the graph
you add an edge every time a befriend event occurs, and remove an edge every time
a defriend event occurs. 

within the process_log.py script, the entire social network connected graph is
built from the batch_log.json file before the processing of the stream logs begins.

the first step in graphing the network is to instantiate the blank network graph
object: G

all batchlog processing is done with the python function "apply_batch_functions"
in the process_log.py file. this function takes two arguments, the batchlog and G
 
apply_batch_functions(batchlog,G)
 
so you feed this function the batchlog starting data, and the empty beginning graph
(or a non-empty beginning graph, for some other use cases) and it will separate
D and T from the first record of the batchlog, sort the batchlog first in timestamp
and then in index, ascending, and process all befriend and defriend events in order,
adding and removing edges from the graph as indicated

the D and T values, batchlog,  and network graph objects are returned

#Streamlog processing and anomaly detection


The streamlog processing starts off a lot like the batch log processing. 
the records are sorted the same way, and befriend and defriend events are handled in order.
the difference lies in the handling of the purchase events. 

in processing purchase order events, the follwing steps are executed:
    obtain ego graph for user graph within parameters d ego_graph = EG(user_id,G,d)

determine purchase history of length t for ego_graph. In other words, query the 
total purchase history for only the purchases which are made by users in the 
ego_graph network (excluding the user theirself)
        
determine statistical anomaly threshhold = mean + (3 * standard deviation)

if currrent order amount >= stastical anomaly threshhold then return a True 
else, return False

#Dependencies


Dependencies for this script are :
    
Python 3.6
Pandas
Numpy
networkx

these can be installed from anaconda package and environment manager 
conda install pandas
conda install numpy
conda install networkx

or the same with pip in a virtualenv


#Testing and test data notes


using the insight_testsuite included with the original repository, this script
passes those tests. However, with the data that came with the original repository,
a T value of 50 was indicated with the test batch logs. Since there are only 3 
purchases in the batch log, this value of 50 for T will obviously never produce 
an anomaly. the test stream log was just one record, intended to be indicated 
as anomalous. A T value of 3 would be the maximum to allow that record to be 
classified, so I manually modified the test input. 


#running the script


the run.sh shell script included does nothing other than 
python ./src/process_log.py

all of the filepath stuff is handled with python magic variables and relative references.


#additional features


1. Adjustment of T value:

upon running if there is no anomalies detected for the value of T provided in
 the batchlogs,the script will prompt for user input asking for different T 
 values, it will also reccomend a T value based on the average network size at 
 time of purchase in the ego graph for the purchaser based on the D value 
 already provided alternate D values will not be suggested.

2. purchases_features.json:

this is an extra output file in the log_output folder. it contains all purchase 
events in the stream logs, and includes a few extra values:
extra columns:

    anomaly = whether or not the row could be an anomaly. this is not the same as
    being flagged, because a flexible T value is used to calculate this
    
    netplen = if netplen is less then T, then this value was used as a T value to 
     create the anomaly flag
 
    TooShort = if this field is marked True, then netplen is less than T, and the 
    anomaly being true does not make the purchase flagged.
    
    mean = network mean used for anomaly calculation

    sd = network standard deviation used for anomaly calculation

    threshhold = mean + (standard deviation * 3)

    T = T value grabbed from batch logs or user input

    D = D value grabbed form batch logs or user input

    flagged = True if anomaly == True and TooShort == False 



assignment from :
https://github.com/InsightDataScience/anomaly_detection
