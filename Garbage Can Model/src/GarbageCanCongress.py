'''
Created on Mar 26, 2014

@author: stran_000
'''
Delimiter = ','  # or \t

from random import choice
from random import random
from random import shuffle
from random import getrandbits
from random import sample
from random import randint
from math import log
from utility import pdf
from utility import cdf
from utility import randomFromCDF
from utility import getTimeStampString
from experiment import Experiment
import traceback
from annealer import Annealer

DEBUG = False
debug_directory = "../test_output/"
def setDebug(val = DEBUG, location = debug_directory):
    global DEBUG, debug_directory
    DEBUG = val
    debug_directory = location

VERBOSE = False
def setVerbose(val = VERBOSE):
    global VERBOSE
    VERBOSE = val
    return val

def verbose(stuff):
    if VERBOSE:
        print(stuff)

Histories_To_File = False
def writeHistories(val = Histories_To_File):
    global Histories_To_File
    Histories_To_File = val
    return val

timestamp = ""
history_file = None
output_vector = []
formatters = []

def setupHistoryFile():
    global history_file
    filename = debug_directory if DEBUG else "../output/"
    filename += "history " + timestamp + ".csv"
    print(filename)
    history_file = open(filename, 'w')

def archive(stuff, formatters=[], file=history_file):
    if file:
        if not formatters:
            file.write(stuff)
        else:
            for idx in range(len(formatters)):
                file.write(formatters[idx]%stuff[idx])
                file.write(Delimiter if idx<len(formatters)-1 else '')
        #history_file.write("\n")
        
def writeRunInfoHeader(file=None):    
    archive("Timestamp: %s\n"%timestamp)
    archive("Unaffiliated fraction: %d\n"%Unaffiliated_Fraction)    
    archive("Green fraction: %0.2f\n"%Green_Fraction)    
    archive("Ideology issues: %d\n"%Ideology_Issues)
    archive("State priorities: %d\n"%State_Priorities)
    archive("\n")
    outputs = ["main issue", "congress init dis", "provisional tally"
               "cosponsors", "cosp init dis", "cosp fin dis",
               "com size", "com init dis", "com fin dis", 
               "# issues", "main issue change", "congress final dis", "votes"]
    formats = ["%s" for output in outputs]
    archive(outputs, formats)
    archive("\n")

Num_of_Representatives = 100
def setNumOfRepresentatives(n = Num_of_Representatives):
    global Num_of_Representatives
    Num_of_Representatives = n
    return n

Num_of_Issues = 10
def setNumOfIssues(n = Num_of_Issues):
    global Num_of_Issues
    Num_of_Issues = n
    return n

Solution_Bit_Length = 3
def setSolutionBitLength(l = Solution_Bit_Length):
    global Solution_Bit_Length
    Solution_Bit_Length = l
    return l

Satisfaction_Threshold = 0.6  # threshold of satisfaction for voting aye on a bill
def setSatisfactionThreshold(threshold = Satisfaction_Threshold):
    global Satisfaction_Threshold
    Satisfaction_Threshold = threshold
    return threshold

PDFCM = 4 # Priority Depth For Committee Membership
Friend_Threshold = 0
Minimum_Friends = 5

#Partisanship Parameters
Unaffiliated_Fraction = 1.0
def setUnaffiliatedFraction(f = Unaffiliated_Fraction):
    global Unaffiliated_Fraction
    Unaffiliated_Fraction = f
    return f

'''
There are two parties:  Green and Yellow.
u = unaffiliated fraction
g = green fraction
N = Unaffiliated + Green + Yellow = N*u + N*(1-u)*g + N*(1-u)*(1-g)
'''
# enum for party IDs
PARTY_NONE = 0
GREEN = 1
YELLOW = 2

Green_Fraction = 0.5  # portion of party-affiliated representatives that are in the "Green" party
def setGreenFraction(f = Green_Fraction):
    global Green_Fraction
    Green_Fraction = f
    return f

Ideology_Issues = 5
# Number of issues each party will prioritize
def setIdeologyIssues(n = Ideology_Issues):
    global Ideology_Issues
    Ideology_Issues = n
    return n

State_Priorities = 5
def setStatePriorities(n = State_Priorities):
    global State_Priorities
    State_Priorities = n
    return n

Ideology_Bit_Depth = 4

Priority_Multiplier = 2

# Annealer values
Min_Temp = 0.01
Max_Temp = 1
Min_Time = 1
Max_Time = 10
Time_Step = 2
k_B = -0.1/log(0.5)  # accept a decrease of 0.1 in satisfaction with a bill with probability 1/2 at temp=1.0

def pdf(values):
    sum_values = sum(values)
    return [v/sum_values for v in values]

def cdf(values):
    distribution = []
    sum_values = sum(values)
    sum_cdf = 0
    for value in values:
        sum_cdf += value/sum_values
        distribution.append(sum_cdf)
    return distribution

def randomFromCDF(distribution):
    # choose an index from distribution given the CDF in distribution
    # note that values in distribution must be monotonically increasing,
    # and distributed in the range (0+,1]!
    r = random()
    index = 0
    while(r > distribution[index]):
        index += 1
    return index

def bitwiseJaccardIndex(a, b):
    c = a^b
    count = 0
    for i in range(Solution_Bit_Length):
        count += (c%2)
        c = c>>1
    return 1 - count/Solution_Bit_Length

def binaryTreeSimilarity(a, b):
    c = a^b
    sim_level = 0.5
    sim = 1.0
    i = 1
    while i <= Solution_Bit_Length:
        if c%2==1:
            sim -= sim_level
        c = c>>1
        sim_level /= 2
        i += 1
    
    return sim

def dumpNetwork(network):
    filename = debug_directory if DEBUG else "../output/"
    adj_filename = filename + "adjacency " + timestamp + ".csv"  #adjacency file
    adj_file = open(adj_filename, 'w')
    
    aff_filename = filename + "affiliation " + timestamp + ".csv" #affiliation file
    aff_file = open(aff_filename, 'w')
    
    # header info for adjacency file
    archive("Timestamp: %s\n"%timestamp, file=adj_file)
    archive("Unaffiliated fraction: %d\n"%Unaffiliated_Fraction, file=adj_file)    
    archive("Green fraction: %0.2f\n"%Green_Fraction, file=adj_file)    
    archive("Ideology issues: %d\n"%Ideology_Issues, file=adj_file)
    archive("State priorities: %d\n"%State_Priorities, file=adj_file)
    archive("\n", file=adj_file)
    
    for i in range(Num_of_Representatives):
        #verbose(network[i])
        for j in range(Num_of_Representatives):
            delim = Delimiter if j<Num_of_Representatives-1 else ''
            adj_file.write("%1.5f %s"%(network[i][j], delim))
        adj_file.write("\n")
        aff_file.write("%d\n"%State.legislators[i].affiliation)
    adj_file.write("\n")
    for i in range(Num_of_Representatives):
        adj_file.write("%1.5f %s"%(sum(network[i]), Delimiter if i<Num_of_Representatives-1 else ''))

class Legislator(object):

    @staticmethod
    def generatePrioritizedNetwork(legislators):
        '''
        Return adjacency matrix based only on homophily
        '''
        matrix = [[0 for i in range(Num_of_Representatives)] for j in range(Num_of_Representatives)]
        for rep1 in legislators:
            i = legislators.index(rep1)
            rep1_issues = sorted(State.issues, key = lambda i: rep1.priorities[i], reverse=True)
            for rep2 in legislators:
                j = legislators.index(rep2)
                if rep1==rep2:
                    rep1.links[rep2] = 1
                    matrix[i][i] = 1
                else:                    
                    link_strength = 0
                    sum_pri_diffs = 0
                    for issue in rep1_issues[0:Ideology_Issues]:
                        similarity = binaryTreeSimilarity(rep1.positions[issue], rep2.positions[issue])
                        pri_diff = 1 - abs(rep1.priorities[issue] - rep2.priorities[issue])
                        link_strength += similarity*pri_diff
                        sum_pri_diffs += pri_diff
                    link_strength = (link_strength/sum_pri_diffs)*2 - 1
                    link = link_strength
                    rep1.links[rep2] = link
                    matrix[i][j] = link
        return matrix
    
    @staticmethod
    def preferentialHomophilyNetwork(legislators):
        '''
        Returns adjacency matrix based on preferential attachment with homophily
        '''
        
        for i in range(Num_of_Representatives):
            legislators[i].linkTo(legislators[i],1)  # create self-link
        for rep1 in sample(legislators, Num_of_Representatives):  # (a shuffle without changing the original list)
            i = legislators.index(rep1)
            rep1_issues = sorted(State.issues, key = lambda i: rep1.priorities[i], reverse=True)
            potential_friends = []
            for rep2 in legislators:  # first find all potential friends with homophily
                j = legislators.index(rep2)
                if rep1!=rep2:                    
                    link_strength = 0
                    sum_pri_diffs = 0
                    for issue in rep1_issues[0:10]:
                        similarity = binaryTreeSimilarity(rep1.positions[issue], rep2.positions[issue])
                        pri_diff = 1 - abs(rep1.priorities[issue] - rep2.priorities[issue])
                        link_strength += similarity*pri_diff
                        sum_pri_diffs += pri_diff
                    link_strength = (link_strength/sum_pri_diffs)*2 - 1
                    if link_strength > Friend_Threshold:
                        potential_friends.append(rep2)
            degrees = [1 for rep in potential_friends]
            for k in range(Minimum_Friends):
                degrees = [len(rep.links.values()) for rep in potential_friends]
                if degrees:
                    friend_idx = randomFromCDF(cdf(degrees))
                    rep2 = potential_friends[friend_idx]
                    rep1.linkTo(rep2, 1)
                    potential_friends.remove(rep2)  # can't friend someone twice
                    
        
        matrix = [[legislators[i].getLinkValueTo(legislators[j]) for i in range(Num_of_Representatives)] 
                                                 for j in range(Num_of_Representatives)]
        return matrix
    
    def linkTo(self, other, value):
        self.links[other] = value
        other.links[self] = value
    
    def getLinkValueTo(self, other):
        return self.links[other] if other in self.links.keys() else 0


    def __init__(self, affiliation, priority_issues=[], default_positions={}):
        self.priorities = {}
        self.positions = {}
        self.links = {} # network link strengths to other legislators
        self.affiliation = affiliation
        
        # generae priorities by preferential attachment
        priorities = [1 for i in range(Num_of_Issues)]        
        for issue in priority_issues:
            priorities[issue] = Priority_Multiplier * (priority_issues.index(issue) + 1)
                    
        for i in range(Num_of_Issues**2):
            priorities[randomFromCDF(cdf(priorities))] += 1
        # normalize the priorities to sum = 1
        priorities = pdf(priorities)
        shuffle(priorities)
        #assign priorities and positions
        for issue in State.issues:
            self.priorities[issue] = priorities[issue]
            self.positions[issue] = getrandbits(Solution_Bit_Length)
            if issue in default_positions.keys():  # set the last bits according to default position
                b = Ideology_Bit_Depth
                #self.positions[issue] = (self.positions[issue]>>b)<<b + default_positions[issue]
                self.positions[issue] = default_positions[issue]
    

    def proposeBill(self):
        #issue = choice(list(self.priorities.keys())) # TODO:  get highest priority issue
        #issues = sorted(list(State.issues), key = lambda issue : self.priorities[issue])
        #issue = issues[-1]
        issue = choice(State.open_issues)
        self.current_proposal = issue
        if issue in State.laws.keys() or issue not in State.open_issues:
            pass
        verbose("\nMain issue: %d" % issue)
        bill = Bill(self, (issue, self.positions[issue]))
        return bill
        
    def pickCoSponsors(self, bill=None):
        cosponsors = []
        for rep in self.links.keys():
            if self.links[rep] > 0.5:
                cosponsors.append(rep)
        return cosponsors
    
    def getSatisfactionWithBill(self, solutions):
        s = 0
        sum_pris = 0
        for issue in solutions.keys():
            # sum up Jaccard indeces for solutions vs positions, weighted by priorities
            s += binaryTreeSimilarity(self.positions[issue], solutions[issue])*self.priorities[issue]
            sum_pris += self.priorities[issue]
        s /= sum_pris # normalize to relevant priorities
        return s

class SmartLegislator(Legislator):
    '''
    Picks co-sponsors based on similarity of the bill main issue
    '''
    def pickCoSponsors(self, bill):
        '''
        Note that with an issue similarity depth of one for network formation, 
        and with only highest-priority issue bills being proposed,
        this method will not be any different than for the base class, since the same set of legislators
        will meet the criteria.
        '''
        cosponsors = []
        for rep in State.legislators:
            support = binaryTreeSimilarity(self.positions[bill.main_issue], rep.positions[bill.main_issue])
            if support > 0.5:
                cosponsors.append(rep)
        return cosponsors

class State(object):

    issues = []
    open_issues = []
    laws = {}  # a dictionary of passed laws (solutions to issues), key: issue;
    legislators = [] 

    def __init__(self):
        global timestamp, formatters
        verbose(timestamp)
        # initialize lawmakers
        State.legislators = []
        State.issues = [i for i in range(Num_of_Issues)]
        State.open_issues = [i for i in range(Num_of_Issues)]
        State.laws = {}
        self.law_count = 0
        self.total_change = 0
        self.votes_tally = 0
        
        u = int(Num_of_Representatives * Unaffiliated_Fraction)  # number of unaffiliated members
        a = Num_of_Representatives - u # number of affiliated members
        g = int(a * Green_Fraction)
        y = a - g
        verbose("Number of Green Representatives: %d"%g)
        verbose("Number of Yellow Representatives: %d"%y)
        
        state_priorities = State.issues[0:State_Priorities]          
        green_issues = sample(State.issues[State_Priorities:], Ideology_Issues) + state_priorities
        yellow_issues = sample(State.issues[State_Priorities:], Ideology_Issues) + state_priorities
        verbose("Green issues: " + str(green_issues))
        verbose("Yellow issues: " + str(yellow_issues))
        green_positions = {}
        yellow_positions = {}
        green_position = 2**(Ideology_Bit_Depth) - 1
        for issue in green_issues:
            green_positions[issue] = green_position
            yellow_positions[issue] = 0
        for issue in yellow_issues:
            yellow_positions[issue] = 0
            green_positions[issue] = green_position
        verbose("Green positions: " + str(green_positions))
        verbose("Yellow positions: " + str(yellow_positions))
        
        for rep in range(u):
            priorities = sample(State.issues[State_Priorities:], Ideology_Issues) + state_priorities
            State.legislators.append(Legislator(PARTY_NONE, priority_issues=priorities))    
        for rep in range(g):
            State.legislators.append(Legislator(GREEN, priority_issues=green_issues, default_positions=green_positions))        
        for rep in range(y):
            State.legislators.append(Legislator(YELLOW, priority_issues=yellow_issues, default_positions=yellow_positions))
                
        #network = Legislator.generatePrioritizedNetwork(State.legislators)
        network = Legislator.preferentialHomophilyNetwork(State.legislators)
        if Histories_To_File:
            dumpNetwork(network)
            setupHistoryFile()
            writeRunInfoHeader()
            
        formatters = ["%d", "%1.4f", "%d", "%d", "%1.4f","%1.4f",
                      "%d", "%1.4f", "%1.4f", "%d", "%1.3f", "%1.4f", "%d\n"]

    def step(self):
        global output_vector
        output_vector = []
        verbose("=================================   New Bill   =======================================================")
        sponsor = choice(State.legislators)
        bill = sponsor.proposeBill()
        output_vector.append(bill.main_issue)
        dis = bill.measureDisSatisfaction(reviewers=State.legislators)
        verbose("Initial legislative body dissatisfaction: %1.4f" % dis)
        output_vector.append(dis)
        votes = self.putToVote(bill)
        output_vector.append(votes)
        
        #circulate draft among cosposnors
        verbose("\nDraft review by Cosponsors:")
        cosponsors = sponsor.pickCoSponsors(bill)
        verbose("Number of cosponsors: %d" % len(cosponsors))
        output_vector.append(len(cosponsors))
        (initial_dis, final_dis) = self.circulateBill(bill, cosponsors)
        output_vector.append(initial_dis)
        output_vector.append(final_dis)
        
        #circulate draft among committee
        verbose("\nCommittee revision:")
        committee = self.getCommitteeMembers(bill)
        verbose("Number of committee members: %d" % len(committee))
        output_vector.append(len(committee))
        (initial_dis, final_dis) = self.circulateBill(bill, committee)
        output_vector.append(initial_dis)
        output_vector.append(final_dis)
        
        # number of issues covered in bill's final form
        provisions = len(bill.solutions.keys())
        verbose("Number of issues addressed: %d" % provisions)
        output_vector.append(provisions)
        bill_change = bill.distanceFromOriginal()
        verbose("Main issue change: %1.3f"% bill_change)
        output_vector.append(bill_change)
        
        # put to vote
        dis = bill.measureDisSatisfaction(reviewers=State.legislators)
        verbose("\nFinal legislative body dissatisfaction: %1.4f" % dis)
        output_vector.append(dis)
        votes = self.putToVote(bill)
        if votes > 0.5*Num_of_Representatives:
            self.makeLaw(bill)
            self.law_count += 1
            self.votes_tally += votes
        verbose("Number of votes: %d" % votes)
        output_vector.append(votes)
        
        archive(output_vector, formatters)
        
    def getCommitteeMembers(self, bill):
        committee = []
        for rep in State.legislators:
            rep_prioritized_issues = sorted(State.issues, key = lambda issue : rep.priorities[issue])
            if bill.main_issue in rep_prioritized_issues[-PDFCM:-1]:
                committee.append(rep)
        return committee

    def circulateBill(self, bill, reviewers):
        if not reviewers:
            reviewers = sample(State.legislators, 5)
        bill.setReviewers(reviewers)
        initial_dis = bill.measureDisSatisfaction()
        verbose("Initial dissatisfaction: %1.4f"%initial_dis)
        revdash = bill.solutions.copy()
        (temps, times) = Annealer.configureLinearSchedule(Min_Temp, Max_Temp, Min_Time, Max_Time, Time_Step)
        revision = Annealer.anneal(revdash, bill.revise, bill.measureDisSatisfaction, k_B, temps, times)
        bill.solutions = revision.copy()
        final_dis = bill.measureDisSatisfaction()
        verbose("Post-revision dissatisfaction: %1.4f"%final_dis)
        return (initial_dis, final_dis)

    def putToVote(self, bill):
        votes = 0
        for rep in State.legislators:
            if rep.getSatisfactionWithBill(bill.solutions) > Satisfaction_Threshold:
                votes += 1
        
        return votes

    def makeLaw(self, bill):
        # TODO - code stuff below
        # transfer bill's solutions to laws dictionary
        # delete issues from legislators' priorities and positions (issues don't resurface once law is passed)
        issues = bill.solutions.keys()
        for issue in issues:
            if issue not in State.open_issues:
                pass
        for issue in issues:
            State.laws[issue] = bill.solutions[issue]
            try:
                State.open_issues.remove(issue)
            except:
                pass
#                 print("***********  ERROR ***********\nIssue %d not found!"%issue)
#                 print("Open issues: %s"%str(State.open_issues))
#                 print("Closed issues: %s"%str(State.laws.keys()))
        self.total_change += bill.distanceFromOriginal()

    
    def closeout(self):
        sat = 0
        if len(State.laws.values())>0:
            for rep in State.legislators:
                sat += rep.getSatisfactionWithBill(State.laws)
        sat /= Num_of_Representatives
        archive("Laws passed: %d\n"%self.law_count)
        archive("Total provisions: %d\n"%len(State.laws.values()))
        archive("Satisfaction with legislation: %1.4f\n"%sat)
        ch = 0 if self.law_count==0 else self.total_change/self.law_count
        archive("avg main issue change: %1.3f\n"%ch)
        return (self.law_count, len(State.laws.values()), sat, ch, self.votes_tally)

class Bill(object):

    def __init__(self, sponsor, issue_proposal):
        (issue, proposal) = issue_proposal
        self.original_issue = issue
        self.original_proposal = proposal
        self.solutions = {}
        self.sponsor = sponsor
        self.solutions[issue] = proposal
        self.main_issue = issue
        self.reviewers = []
        
    def distanceFromOriginal(self):
        distance =  1 - binaryTreeSimilarity(self.original_proposal, self.solutions[self.main_issue])
        return distance
        
    def setReviewers(self, reviewers):
        self.reviewers = reviewers

    def revise(self, solutions):  # move bill to a neighbor in state-space
        revision = solutions.copy()
        if State.open_issues:
            issue = choice(State.open_issues)
        else:
            issue = choice(list(solutions.keys()))
        # or pick one of the existing reviewers to choose an issue to revise according to reviewer's position
        bit = choice(range(Solution_Bit_Length))
        mask = 2**bit
        if issue in solutions.keys():  # if the issue is currently in the issues list,
            revision[issue] = revision[issue]^mask  # invert the bit in the current solution
        else:  # otherwise add it to the bill's issues list, with a random position on that issue
            revision[issue] = randint(0, (2**Solution_Bit_Length)-1) 
        return revision
            
    def measureDisSatisfaction(self, solutions=None, reviewers=None):  # objective function
        if not reviewers:
            reviewers = self.reviewers
        if not solutions:
            solutions = self.solutions
        E = 0
        for reviewer in reviewers:
            E += reviewer.getSatisfactionWithBill(solutions)
        E /= len(reviewers)
        return -E
    

def runOnce():
    global timestamp
    timestamp = getTimeStampString()
    setDebug(True)
    setVerbose(False)
    writeHistories(True)
    setSolutionBitLength(4)
    setNumOfIssues(50)
    setNumOfRepresentatives(100)
    
    setSatisfactionThreshold(0.5)
    setUnaffiliatedFraction(0.05)
    setGreenFraction(0.5)
    setIdeologyIssues(5)
    setStatePriorities(5)
    proposals = 200
    archive("Number of proposals: %d\n"%proposals)
    s = State()
    for i in range(proposals):
        if State.open_issues:
            s.step()
    s.closeout()

          
if __name__ == "__main__":
    runOnce()
