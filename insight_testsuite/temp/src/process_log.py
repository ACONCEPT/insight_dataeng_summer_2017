import pandas as pd
import os 
import numpy as np
import networkx as nx
import json

class HistTooShort(Exception):
    def __init__(self,*args,**kwargs):
        Exception.__init__(self,*args,**kwargs)           

def get_batchlog(full_data = False):
    """ 
    get full set of batchlog data for building network starting state
    """ 
    small_data = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/log_input/batch_log.json'
    bigger_data = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/sample_dataset/batch_log.json'
    if full_data:        
        source = bigger_data 
    else:
        source = small_data 
    print ('reading batch logs from {}'.format(source))
    data = pd.read_json (source, lines = True)
    return data

#def get_stream_data(full_data = False): 
def get_streamlog(full_data = False):
    """ 
    get full set of stream data for flagging
    """ 
    small_data = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/log_input/stream_log.json'
    bigger_data = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/sample_dataset/stream_log.json'
    if full_data:
        source = bigger_data 
    else:
        source = small_data        
    print ('reading stream logs from {}'.format(source))
    data = pd.read_json(source,lines = True)
    return data 
    
        
def d_t (batchlog):
    """
    separates out the D and T values from the batchlog
    ADD [CHECK IF THERE IS MORE THAN ONE SET OF D AND T VALUES]
    """ 
    dt = batchlog[(np.isfinite(batchlog['D'])) & (np.isfinite(batchlog['T']))]
    batchlog = batchlog.query('index != {}'.format(int(dt.index[0])))    
    del dt['amount']
    del dt['event_type']
    del dt['id']
    del dt['id1']
    del dt['id2']
    return dt, batchlog  

def apply_batch_functions(batchlog,G):
    """ 
    separate out special D and T row
    add edges for "befriend" events
    remove edges for "unfriend" events 
    do this in order of timestamp/id
        
    """ 
    print('applying batch functions')
    def batch_functions(row):   
        if row['event_type'] == 'unfriend':
            G.remove_edge(row['id1'],row['id2'])
        if row['event_type'] == 'befriend':
            G.add_edge(row['id1'],row['id2'])            
    batchlog.sort_values('timestamp', axis = 0,  ascending = True)
    dt, batchlog = d_t(batchlog)
    D = dt['D'][0]
    T = dt['T'][0]
    batchlog.apply(batch_functions,axis = 1)
    return dt, batchlog, D, T, G

def ego_graph(full_graph, user_id, depth):
    return nx.ego_graph(full_graph, user_id, depth, center = False) 

def network_purchases(eg, all_purchases): 
    netp = all_purchases[all_purchases.id.isin(eg.nodes())]    
#    print(len(netp))
    netp_sorted = netp.sort_values(by = 'timestamp', axis = 0, ascending = False)
    return netp_sorted


def isanomaly(user_id, G, d, current_purchaselist, t, amount):
    """
    obtain ego graph for user graph within parameters d ego_graph = EG(user_id,G,d)
    determine purchase history of length t for ego_graph, purchase_history = PH(ego_graph,current_purchaselist,t)
        raise HistTooShort exception if total purchase histor of the ego graph's network is less t
            in other words, if len(purchase_history)  < t raise HistTooShort exception 
    determine statistical anomaly threshhold = SAT(ego_graph, purchase_history)
    if currrent order amont >= stastical anomaly threshhold then return a True
    else, return False
    """ 
    eg = ego_graph(G,user_id,d)
    
    netp = network_purchases(eg,current_purchaselist)
    
    if len(netp ) < t: 
        TooShort = True
        t = len(netp )        
    else: 
        TooShort = False
        
    netp_t = netp [:int(t)]    
    mean = np.mean(netp_t.amount)
    
    std = np.std(netp_t.amount)
    thresh = mean + (std * 3)
    
    if amount >= thresh:
        result = True
    else: 
        result = False
    return result, TooShort, mean, std, thresh, t, len(netp)

def apply_stream_functions(streamlog,current_purchaselist,G,D,T,T_override = False):    
    print ('applying stream functions')
    def stream_functions(row): 
        anomaly = False
        TooShort = False
        flagged = False
        purchase = False
        mean = np.nan
        std = np.nan
        threshhold = np.nan
        t = np.nan
        netplen = np.nan
        
        if row.event_type == 'unfriend':
            G.remove_edge(row['id1'],row['id2'])                        
            anomaly = False
            
        if row.event_type == 'befriend':
            G.add_edge(row['id1'],row['id2'])            
            anomaly = False
            
        if row.event_type == 'purchase':
            purchase = True
            anomaly, TooShort, mean, std, threshhold , t , netplen = isanomaly(row['id'],G,D,current_purchaselist,T,row['amount'])                 
            current_purchaselist.append(row)
            
        if not TooShort and anomaly and purchase:
            flagged = True
        elif T_override and anomaly and purchase:
            flagged = True            
            
        row['anomaly']  = anomaly        
        row['TooShort'] = TooShort
        row['mean'] = mean
        row['sd'] = std
        row['threshhold'] = threshhold
        row['T'] = T
        row['D'] = D
        row['flagged'] = flagged
        row['ispurchase'] = purchase
        row['netp_length'] = netplen
        
        return row  
    

    streamlog.sort_values('timestamp', axis = 0,  ascending = True)
    classified_purchases = streamlog.apply(stream_functions,axis = 1)    
    
#    anomalies = classified_purchases.query("anomaly == True")
#    del anomalies['anomaly']
    
    return classified_purchases, G

def format_output(flagged):
    del flagged['anomaly']
    del flagged['TooShort']
    del flagged['flagged']
    del flagged['ispurchase']
    del flagged['netp_length']
    del flagged['threshhold']
    del flagged ['T']
    
    flagged['timestamp'] = flagged['timestamp'].strftime('%Y-%m-%d %H:%M:%S')    
    flagged['id'] = str(flagged['id'])
    flagged['amount'] = str(flagged['amount'])
    
    mean = round(flagged['mean'],2)
    flagged['mean'] = '{:.2f}'.format(mean)
    
    sd = round(flagged['sd'],2)
    flagged['sd'] = '{:.2f}'.format(sd)
    
    flagged = flagged[['event_type','timestamp','id','amount','mean','sd']]       
    
#    flagged = flagged.round(2)
    return flagged

def print_stats():
    pass

def prompt_dt(D,T,classified):
    anomalies = classified.query('anomaly == True')
    print('No anomalies detected for D value of {} and T value of {}'.format(D,T))
    print('suggested T value is {}'.format(classified['anomaly_t'].mean(axis=0)))
    d = int(input('please enter new integer value for D : '))
    t = int(input('please enter new integer value for T : '))
    return d, t 

def do_batchlogs(fulldata,G):
    batchlog = get_batchlog (fulldata)
    dt, batchlog, D, T, G = apply_batch_functions(batchlog,G)    
    batchpurchases = batchlog.query("event_type == 'purchase'")
    return dt, batchlog, D, T, G, batchpurchases

def do_streamlogs(fulldata,batchpurchases,G,D,T):
    streamlog = get_streamlog (fulldata) 
    classified, G = apply_stream_functions(streamlog,batchpurchases,G,D,T) #anomalies, classified_purchases ,     
    return classified, G 
    
def main (fulldata = False): 
    """ 
    1. instantiate graph object (G)
    2. obtain batch logs (historic data)
    3. build starting social graph on G
        if freind, add edge
        if defreind, remove edge
        nodes are populated automatically from adding edges
    4. separate purchases from historic data
    5. obtain stream logs (data that would be live from an API)
    6. loop through stream data beginning to end
        1. update overall social graph
        2. evlauate each purchase for anomalous status
        (see docstring on "is_anomalous" in order to get full break down here)
    """ 
    # 1
    G = nx.Graph()    
    
    #2 + 3 + 4
    dt, batchlog, D, T, G, batchpurchases = do_batchlogs(fulldata,G)
    print('nodes {} , edges, {} in starting network'.format(str(G.number_of_nodes()),str(G.number_of_edges())))    
        
    #5 + #6    
    classified, G = do_streamlogs(fulldata,batchpurchases,G,D,T)    
    print('nodes {} , edges, {} after stream'.format(str(G.number_of_nodes()),str(G.number_of_edges())))              
    
    flagged_purchases = classified.query('flagged == True')    
    
    if len(flagged_purchases)  == 0: 
        d, t = prompt_dt(D,T,classified)
        if int(d) != int(D) or int(t) != int(T): 
            classified, G = do_streamlogs(fulldata,batchpurchases,G,d,t)    
            flagged_purchases = classified.query('flagged == True')
            print ('with D = {} and T = {} you found {} anomalies'.format(d,t,len(flagged_purchases)))            
            
    flagged = flagged_purchases.apply (format_output, axis = 1)
    
    outfile = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/log_output/flagged_purchases.json'
    print (" saving flagged purchases to : {} ".format(outfile))
    flagged.to_json(outfile, orient = 'records', lines = True )    
    
    outfile = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/log_output/purchases_features.json'
    print (" saving flagged purchases to : {} ".format(outfile))
    classified.to_json(outfile, orient = 'records', lines = True )    
#    with open(outfile,'a') as output:
#        output.write("""
#""")

    print("""
          
=============================================
             anomaly(True) = {}
             anomaly AND tooshort = {}
             anomaly(False) = {}
             TooShort(count) = {} 
             purchaes(count)  {}
             flagged(count) = {}
             avg ntwrk hist size = {}
             min ntwrk hist size = {} 
             max ntwrk hist size = {} 
             D value = {}
             T value = {} 
=============================================
""".format(
        len(classified.query('anomaly == True')),
        len(classified.query('anomaly == True & TooShort == True')),
        len(classified.query('anomaly == False')),
        len(classified.query("TooShort == True")),
        len(classified.query("ispurchase == True")),
        len(classified.query("flagged == True")),
        str(round(classified.netp_length.mean(),2)),
        classified.netp_length.min(),
        classified.netp_length.max(),
        D,
        T
        ))
    
    return flagged , classified , D, T , batchlog , batchpurchases, G

if __name__ == '__main__':
    flagged , classified , D, T , batchlog, batchpurchases, G = main(False)
    
    




