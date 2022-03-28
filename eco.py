#This program runs a simulation of the economy.
#Each digital person goes out and spendsa certain amount of money every day.
#Each act of spending involves giving their money to other people.
#Some goods and services are produced by many people, so the money spent may be split between those people.
#The expected result is that some people's wealth will increase, and others will decrease

#Is this an accurate simulation of the economy?
#The instinctual answer might be to say, "of course not!"
#"People are given more money based on how hard they work, right?"
#However, how do we define "hard work?" If money represents how hard
#you work because you are given money for working hard, you've fallen
#into a kind of circular logic. Until there becomes some independent
#metric for "hard" or "desireable" work, we can't assume wealth is
#a representation of anything.

#The stock market is unpredictable. While trends can appear, they can
#also reverse. And the biggest trend of all is demonstrated by this program:
#those with wealth will increase their wealth. Those without wealth, will
#tend to lose wealth.

from pprint import pprint
import random
import locale
from sklearn.linear_model import LinearRegression
import numpy as np
import math
import copy

CURRENCY_FORMAT = ''
DEFAULT_DISPLAY = {
    "graph" : {
        "type" : "scatter",
        "x-axis" : "time",
        "y-axis" : "array",
        "line_of_equality" : False
    },
    "table" : {
        "columns" : ["Value1", "Value2"]
    },
    "stats" : {}
}

E = 2.7182818284

preferences = {
    "GDP" : {"calculate":10},
    "income" : {"calculate":30},
    "default_depreciation" : {"days" : 30, "percent" : 0.1},
    "credit": {
        "loans":{
            "normal_interest_rate":10,
            "standard_deviation":1
            },
        "initial_credit_risk" : 0.1,
        "credit_score" : {
            "benchmark":600, 
            "minimum_payment_reward" : 5, 
            "delinquency_penalty" : 15, 
            "partial_payment_penalty" : 7,
            "default_penalty" : 100,
            "bankruptcy_penalty" : 300
            },
        "credit_analysts" : {"debtors_required_to_be_an_analyst" : 5}
    },
    "print_logs" : True,
    "print_achievements" : True
}

INITIAL_CREDIT_SCORE = preferences["credit"]["credit_score"]["benchmark"]
INITIAL_CREDIT_RISK = preferences["credit"]["initial_credit_risk"]

locale.setlocale(locale.LC_ALL, CURRENCY_FORMAT)

class Data():
    def __init__(self, data=[], properties=DEFAULT_DISPLAY, display="graph", name="", x_value=False, line=None):
        self.name = name
        self.x_value = x_value
        self.line = line
        if display == "graph":

            if x_value and data.size > 1:
                for i in range(2):
                    if type(data[i]) is list:
                        np.array(data[i])
            else:
                if type(data) is list:
                    np.array(data)

            self.data = data

        elif display in ["table","stats"]: #stats will be a dict
            self.data = data

        self.properties = properties #data properties can be stored as dict or json
        self.display = display

    def append(self, data):
        self.data = np.append(self.data, data)

    def to_string(self):
        return self.name

class Society():
    def __init__(self, population, money_reserves, variety_of_jobs=100, max_employees=100,
            egalitarian=True, will_grow=False, money_supply_will_increase=False, has_debt=True,
            redistribution_factor=0, interest_rate=0.005, name="Society 1", faith_in_credit_score = 0):
        
        global achievements
        achievements = [] #TODO: 
        global logfile
        logfile = name.replace(" ", "_") + "_log.txt"
        clear_logs()
        clear_achievements()

        self.name = name

        self.money_reserves = money_reserves
        self.population = population
        self.variety_of_jobs = variety_of_jobs
        self.max_employees = max_employees
        self.egalitarian = egalitarian
        self.will_grow = will_grow
        self.money_supply_will_increase = money_supply_will_increase
        self.has_debt = has_debt
        self.redistribution_factor = redistribution_factor
        self.average_income = 0
        

        self.people = []
        self.products = []
        self.jobs = [] #bankers are -1
        self.bankers = []

        ################################
        #
        #           Finance
        #
        ################################

        self.debts = []
        self.average_principle = 0 #average size of each individual debt asset (not individual debt)
        self.average_delinquency = 0
        self.default_rate = 0
        self.interest_rate = interest_rate
        self.average_commercial_interest_rate = interest_rate
        self.credit_score_benchmark = preferences["credit"]["credit_score"]["benchmark"]
        self.average_credit_score = preferences["credit"]["credit_score"]["benchmark"]
        self.credit_risk = INITIAL_CREDIT_RISK
        self.faith_in_credit_score = faith_in_credit_score #average of all lendors faith in the credit score
        self.credit_score_standard_deviation = 0
        
        self.day = 0
        for p in range(population):
            self.people.append(Person(money_reserves/population, random.randint(18,50), self))

        self.mc = 0.0 #Market Cumulation (probably made up)
        self.gdp = None #gross domestic product
        self.gdp_sum = 0.0
        self.last_gdp = None
        self.inequality = 0.0 #TODO: Include assets
        self.consumer_debt = 0.0

        lorenz_properties = copy.deepcopy(DEFAULT_DISPLAY)
        lorenz_properties["graph"]["line_of_equality"] = True

        self.graphs = [
            Data(data=self.gdp, name="Gross Domestic Product"),
            Data(data=self.mc, name="Market Cumulation"),
            Data(data=self.inequality, name="Inequality/Time"),
            Data(name="Inequality (Lorenz)", line=1),
            Data(data=self.credit_risk, name="Credit Risk"),
            Data(data=self.faith_in_credit_score, name="Faith in Credit Score"),
            Data(data=self.average_commercial_interest_rate, name="Commercial Interest Rates")
        ]

    ###########################
    #
    #    DATA
    #
    ###########################

    def update_graphs(self, special_data=[[]]):
        #GDP calculated elsewhere
        self.graphs[1].data = np.append(self.graphs[1].data, self.mc)
        self.graphs[2].data = np.append(self.graphs[2].data, self.inequality)
        self.graphs[3].data = lorenz_curve(special_data)
        self.graphs[4].data = np.append(self.graphs[4].data, self.credit_risk)
        self.graphs[5].data = np.append(self.graphs[5].data, self.faith_in_credit_score)
        self.graphs[6].data = np.append(self.graphs[6].data, self.average_commercial_interest_rate)

    def update(self):

        ##########################
        #
        #    Loop through People
        #
        #########################

        wealth_per_person = []
        commodity_values = []
        credit_scores = []
        credit_faith_sum = 0
        credit_analyst_sum = 0
        calc_income = False
        if self.day != 0 and self.day % preferences["income"]["calculate"] == 0:
            total_income = 0
            calc_income = True
        for person in self.people:
            person.live_one_day()
            wealth_per_person.append(person.wealth)
            credit_scores.append(person.credit_score)
            if calc_income:
                total_income+=person.income
            if person.credit_analyst:
                credit_faith_sum += person.faith_in_credit_score
                credit_analyst_sum += 1
            if person.cash < 0:
                print("WARNING: Negative cash has been created!")
        if calc_income:
            self.average_income = total_income / len(self.people)
        if credit_analyst_sum > 0:
            self.faith_in_credit_score = credit_faith_sum / credit_analyst_sum #average credit analyst's analysis of credit
        
        for commodity in self.products:
            commodity_values.append(commodity.value)

        #TODO: space out and/or stagger more measurements like GDP
        if self.day != 0 and self.day % preferences["GDP"]["calculate"] == 0:
            self.gdp = self.gdp_sum #gdp current
            self.last_gdp = self.gdp_sum #last calculated gdp
            self.gdp_sum = 0.0
            

        self.inequality = gini(wealth_per_person)
        #print(commodity_values)
        self.mc = sum(commodity_values) #TODO: don't count unfinished goods, ...

        if self.gdp != None:
            self.graphs[0].data = np.append(self.graphs[0].data, self.gdp)
            self.gdp = None

        money_count = 0 #TODO: do this in longer intervals
        for person in self.people:
            money_count += person.cash
        self.money_reserves = money_count
        self.log(format_currency(self.money_reserves))

        ####################################
        #
        #   Loop through debts (or copy lists for somereason?) #TODO: check performance
        #
        #####################################

        self.debts = [d for d in self.debts if d.principle > 0]
        if len(self.debts) > 0:
            self.average_principle = sum([d.principle for d in self.debts])/len(self.debts)
            self.average_commercial_interest_rate = sum([d.interest_rate for d in self.debts])/len(self.debts)
            self.average_delinquency = len([d for d in self.debts if d.delinquent])/len(self.debts)
            if len([d for d in self.debts if d.defaulted]) != 0:
                self.default_rate = sum([d.principle for d in self.debts if d.defaulted])/len([d for d in self.debts if d.defaulted]) / self.consumer_debt #TODO: add cunsumer and business debt
            self.average_credit_score = sum(credit_scores)/len(credit_scores)
            avg = self.average_credit_score
            self.credit_score_standard_deviation = get_sigma(credit_scores, avg, self.population)
            self.calculate_credit_risk()

        self.log("Average Debt: " + format_currency(self.average_principle))
        self.log("Average Delinquency: " + str(self.average_delinquency))
        self.log("Default Rate: " + str(self.default_rate)) #per dollar
        self.log("Bankers: "+str(len(self.bankers)))
        self.log("Consumer Debt: "+str(self.consumer_debt))
        self.log("Faith in credit score: "+str(self.faith_in_credit_score))
        self.log("Average Income: "+str(self.average_income))
        self.log("Average Interest Rate: "+str(self.average_commercial_interest_rate))
        self.log("Average Credit Score: "+str(self.average_credit_score))
        self.log("Credit Risk: "+str(self.credit_risk))
        print()

        #Do this last
        self.update_graphs(special_data=[wealth_per_person])


    ##########################
    #
    #  Economic Functions
    #
    ##########################

    def give(self, person, amount, account): #TODO: taxes based on income?
        for reciever in self.people:
            if person == reciever:
                reciever.cash += amount
                reciever.update_bank_statement(self.day, amount, account, reciever.cash)
                reciever.accounts_receivable.append(amount)

    def add_banker(self):
        most_cash = 0 #someone must have positive cash
        richest_non_banker = None
        for person in self.people:
            if person.cash > most_cash and person.trade != -1:
                most_cash = person.cash
                richest_non_banker = person
        richest_non_banker.trade = -1
        richest_non_banker.highlight = True
        self.jobs.append(Job(-1, self))
        self.bankers.append(richest_non_banker)
        return richest_non_banker

    def calculate_credit_risk(self):
        #old formuala: self.credit_risk = pow(c, -(1/b)*a+d) + 1
        credit_risk = max (len([d for d in self.debts if d.defaulted]) / len(self.debts) * 100, 1) / 100
        if not credit_risk >= 1:
            self.credit_risk = credit_risk
        else:
            log("WARNING: credit risk of 100% (I hope the p-value is high this time.)")


    #########################
    #
    #     Boiler Plate
    #
    #########################

    def get_string(self, var_name): #gets a list of strings that represent that object type
        for k,v in self.__dict__.items():
            if k == var_name:
                if type(v) is list:
                    lst = []
                    for item in v:
                        lst.append(item.to_string())
                    return lst
                else:
                    return v.to_string()

    def get(self, var_name): #gets a list of everything with that className
        for k,v in self.__dict__.items():
            if k == var_name:
                return v

    def log(self, message):
        log_message = str(self.day) + "  "+self.name+"  " +message+"\n"
        with open(logfile, 'a') as l:
            l.write(log_message)
        if preferences["print_logs"] == True:
            print(log_message)

class Person():
    def __init__(self, initial_cash, age, society, birthday=random.randint(1,365), spending_habits=0.05,
        risk_tolerance = None):

        self.highlight = False #highlight in menu pane
        self.id = len(society.people) + 1
        self.generate_name()

        self.wealth = 0
        self.cash = initial_cash #TODO: initial cash var?
        self.initial_cash = initial_cash
        self.spending_habits = spending_habits
        self.age = age
        self.society = society
        self.birthday = birthday
        self.days_until_next_birthday = 365 - birthday
        #what job does this person have?
        self.trade = random.randint(0,society.variety_of_jobs-1)
        #add their job to the economy
        self.society.jobs.append(Job(self.trade, society))

        ###########################3
        #
        #  Debt
        #
        ###########################

        #
        # Borrowing
        #

        self.debt = 0.0
        self.debts = []
        self.percent_delinquent = 0
        self.percent_defaulted = 0
        self.amt_debt_defaulted = 0
        self.debtors = []

        #
        # Lending
        #

        self.faith_in_credit_score = society.faith_in_credit_score #only changes if they are a lender
        self.credit_analyst = False
        self.last_charged_interest = 0.0
        self.credit_score = INITIAL_CREDIT_SCORE
        self.debtors_default_rate = np.array([])
        self.credit_scores_of_debtors = np.array([])


        self.spending = []
        self.bank_statement = [[],[],[],[]]
        self.property = []
        self.accounts_receivable = []
        self.income = 0

        if risk_tolerance == None:
            mu = preferences["credit"]["loans"]["normal_interest_rate"]
            sigma = preferences["credit"]["loans"]["standard_deviation"]
            self.risk_tolerance = np.random.normal(mu, sigma, 1)[0] #smaller risk taking, smaller loans taken. also represents % interest willing to take
        else:
            self.risk_tolerance = risk_tolerance

        self.stats = {}
        
        bank_properties = copy.deepcopy(DEFAULT_DISPLAY)
        bank_properties["table"]["columns"] = ["Date", "Amount","Account","Balance"]
        
        
        self.display_objects = [
            Data(name="Wealth"),
            Data(name="Cash"),
            Data(name="Spending", data=self.spending),
            Data(name="Bank Statement", data=self.bank_statement, display="table", properties=bank_properties),
            Data(name="Credit Score"),
            Data(name="Faith in Credit Score", data=self.faith_in_credit_score),
            Data(name="Income"),
            Data(name="Loan Default Rate", data=np.array([[],[],0], dtype=object), x_value=True, line=True),
            Data(name="Stats",data=self.stats,display="stats")
        ]
        self.set_stats()
        
    def update_display_objects(self):
        self.display_objects[0].data = np.append(self.display_objects[0].data, self.wealth) #single numbers
        self.display_objects[1].data = np.append(self.display_objects[1].data, self.cash)
        self.display_objects[2].data = np.array(self.spending) #arrays
        self.display_objects[3].data = self.bank_statement #table data
        self.display_objects[4].data = np.append(self.display_objects[4].data, self.credit_score)
        self.display_objects[5].data = np.append(self.display_objects[5].data, self.faith_in_credit_score)
        self.display_objects[6].data = np.append(self.display_objects[6].data, self.income)
        #7 is caculated elsewhere
        self.set_stats()

    def live_one_day(self):
        
        self.daily_expense = 0.0
        if self.debt > 0.0:
            for d in self.debts:
                #debt increases without any transaction
                d.add_interest()
                
        self.work()
        self.spend(self.initial_cash*self.spending_habits) #spends a percent of his initial cash every day 
        #TODO: multiply by inflation here?
        self.days_until_next_birthday -= 1
        if self.days_until_next_birthday == 0:
            self.days_until_next_birthday = 365
            self.age+=1

        property_value = 0
        for product in self.property:
            product.depreciate_one_day()
            property_value += product.value
        self.property_value = property_value
        self.calculate_wealth()

        if len(self.debts) > 0:
            self.percent_delinquent = len([d for d in self.debts if d.delinquent])/len(self.debts)
            self.percent_defaulted = len([d for d in self.debts if d.defaulted])/len(self.debts)

        if len(self.debtors) > self.society.population * (preferences["credit"]["credit_analysts"]["debtors_required_to_be_an_analyst"]/100): #5% of the population owes them money
            self.calculate_faith_in_credit_score()
        else:
            self.faith_in_credit_score = self.society.faith_in_credit_score

        if self.society.day != 0 and self.society.day % preferences["income"]["calculate"] == 0:
            self.calculate_income()

        self.update_display_objects()

    def calculate_income(self):
        self.income = sum(self.accounts_receivable)
        self.accounts_receivable = []

    def calculate_wealth(self):
        debt_count = 0
        for d in self.debts:
            debt_count += d.principle
            self.debt = debt_count
       
        self.wealth = self.cash + self.property_value - self.debt

    def work(self):
        for commodity in self.society.products:
            if commodity.trade_index == self.trade:
                if commodity.job.workers_required > len(commodity.workers_used):
                    commodity.workers_used.append(self)
                    if commodity.is_finished(): #check if the product is now finished
                        self.society.gdp_sum += commodity.value
                    return
        commodity = Commodity(self.trade, self, self.society)
        self.society.products.append(commodity)
        if commodity.is_finished():
            self.society.gdp_sum += commodity.value

    def spend(self, amount):
        if len(self.society.products) > 0: #there must be something to buy
            if self.cash-amount < 0:
                if (not self.society.has_debt):
                    #if society doesn't allow debt
                    #   person can't borrow
                    self.spending.append(0.0)
                    return
                else:
                    #calculate interest rate
                    d = Debt(self.society, amount+amount*self.risk_tolerance, self, None)
                    interest_rate = d.calculate_interest_rate(amount, self, self.society)
                
                if interest_rate == None or self.is_too_risky(
                        interest_rate): #bank denied loan or risk was too much
                    self.spending.append(0.0) 
                    if interest_rate != None:
                        self.society.log(self.name + " decided not to take a loan at "+str(round(interest_rate*100)) + "%")
                        if interest_rate < 0.02:
                            #achievement get
                            log("\"I don't believe in debt:\" Someone refused a debt at less than 2% interest") #TODO: poisson will make this rare
                    return
                else: #borrow the money
                    self.borrow(d, interest_rate=interest_rate)

            self.buy(random.randint(0,len(self.society.products)-1), amount)
            self.spending.append(self.daily_expense)

    def is_too_risky(self, interest_rate):
        if interest_rate > self.risk_tolerance/100: #TODO: adjust to poisson
            return True
        else:
            return False

    def borrow(self, debt, interest_rate=None):
        if debt.loan > self.society.money_reserves:
            #Acheivement get
            log("\Pay You Back With Interest\" Somebody borrowed more cash than there is money.")
        #self.debt += amount ...calculate when calculating wealth
        available_bankers = self.society.bankers[:]
        if self.trade == -1: #do not borrow from self
            available_bankers.remove(self)

        available_bankers = [b for b in available_bankers if b.cash >= debt.loan]
        
        if len(available_bankers) == 0: #if there are no bankers, make one
            lender = self.society.add_banker()
            debt.set_creditor(lender)
            self.debts.append(debt)
        elif len(self.debts) > 0: #if there are bankers, do we already owe one?
            #look for the best deal
            lowest_interest_rate = 1
            better_deal_found = False
            for r in self.debts:
                if r.interest_rate < lowest_interest_rate:
                    lowest_interest_rate = r.interest_rate
            for b in available_bankers:
                #TODO: account for credit score here
                if b.last_charged_interest < lowest_interest_rate: #lenders last charged interest may vary
                    lender = b
                    debt.set_creditor(lender)
                    #add a new debt
                    self.debts.append(debt)
                    better_deal_found = True
                    return
            if not better_deal_found:
                d = random.choice(self.debts)
                if d.creditor in available_bankers:
                    d.increase(debt.loan)
                else:
                    lender = random.choice(available_bankers)
                    debt.set_creditor(lender)
                    self.debts.append(debt)
        else: #if we don't owe anyone... we do now
            lender = random.choice(available_bankers)
            debt.set_creditor(lender)
            self.debts.append(debt)
        if self.cash < 0:
            print("WARNING: Negative cash has been created!")

    def buy(self, commodity_index, amount):
        #They can't buy what they need if the product isn't finished
        if len(self.society.products[commodity_index].workers_used) == self.society.products[commodity_index].job.workers_required:
            
            #Pay the daily cost of living (if possible)

            self.cash-=amount
            self.daily_expense += amount
            commodity = self.society.products.pop(commodity_index)
            commodity.set_value(amount) #TODO: set initial price by labor theory of value, change price by supply and demand
            self.property.append(commodity)
            self.update_bank_statement(self.society.day, -amount, commodity.trade_index, self.cash)
            
            for other_commodity in self.society.products:
                if other_commodity.trade_index == commodity.trade_index:
                    other_commodity.set_value(amount) #TODO: balance this feature
            for person in commodity.workers_used: #TODO: or vendor if no workers used
                self.society.give(person, amount/len(commodity.workers_used), self.name)
            
            #Service debt with remaing cash

            if self.debt > 0.0:
                if self.cash > 1.0:
                    self.service_debt()
                else:
                    for d in self.debts:
                        if d.minimum_payment > 0:
                            d.delinquency(0)

            #TODO: add disposible income?

    def service_debt(self):
        
        debt_expense = 0
        extra_debt_expense = 0
        #sort debts by highest to lowest interest rate
        self.debts.sort(key=lambda x: x.interest_rate, reverse=True)

        #self.owe.cash+=amount
        #TODO: pay as much as they can across all debts

        if self.debt > self.society.money_reserves:
            #acheivment get
            achievement(0, "\"That's the Bank's Problem\" One person has more debt than there is money.")

        i = 0
        debts_to_remove = []
        for d in self.debts:
            if d.minimum_payment + d.back_payments > 0: #if we haven't paid yet
                #if we have the money, pay
                if self.cash - d.minimum_payment - d.back_payments > 0:
                    debt_expense += min([d.minimum_payment+d.back_payments, self.cash])
                    d.decrease(debt_expense)
                    self.calculate_wealth() #recalculate debt value before removing debts #TODO: wealth metric will help when selling stuff to pay off debts
                    if d.principle == 0.0:
                        debts_to_remove.append(d)
                else: #didn't have enough money for minimum payment
                    if d.minimum_payment + d.back_payments > 0:
                        d.delinquency(self.cash) #partial payment
                        break
                i+=1

        for d in debts_to_remove:
            d.remove_debt()

        debts_to_remove = []
        
        if self.cash > 0: #if we have any money left pay more debts
            j = 0
            for d in self.debts:
                extra_debt_expense += min([self.cash, d.principle])
                d.decrease(extra_debt_expense)
                self.calculate_wealth() #recalculate debt value before removing debts #TODO: wealth metric will help when selling stuff to pay off debts
                if d.principle == 0.0:
                    debts_to_remove.append(d)
                if self.cash <= 0:
                    if self.cash < 0:
                        print("WARNING: Negative cash has been created!")
                    break
                j += 1

        for d in debts_to_remove:
            d.remove_debt()

        self.daily_expense += debt_expense + extra_debt_expense

    
        #TODO: class Banker(Person), CreditAnalyst(Banker)


    def calculate_faith_in_credit_score(self):
        X = np.array([[(p.credit_score) for p in self.debtors]]).reshape(-1,1)
        Y = np.array([[(-p.amt_debt_defaulted) for p in self.debtors]]).reshape(-1,1) #we know their default rate for other loans as well
        self.credit_scores_of_debtors = X
        self.debtors_default_rate = Y
        linear_regressor = LinearRegression(fit_intercept=True)
        linear_regressor.fit(X, Y)
        r = linear_regressor.score(X, Y)
        coef = linear_regressor.coef_
        line_slope = coef[0]
        self.faith_in_credit_score = r
        self.credit_analyst = True #these people set the society's faith in the credit score

        self.display_objects[7].data = np.array([self.credit_scores_of_debtors, self.debtors_default_rate], dtype=object)
        self.display_objects[7].line = line_slope


    def generate_name(self):
        self.name = "Bill"

    def set_stats(self):
        self.stats = {
            "Name" : self.name,
            "Age" : self.age,
            "Trade" : self.trade,
            "Wealth" : self.wealth,
            "Cash" : self.cash,
            "Spending Habits" : str(self.spending_habits*100) + "%/day",
            "Property" : self.property
        }
        self.display_objects[-1].data = self.stats #stats always last

    def update_bank_statement(self, day, amount, company, balance):
        self.bank_statement[0].append(day)
        self.bank_statement[1].append(format_currency(amount)) 
        self.bank_statement[2].append(company)
        self.bank_statement[3].append(format_currency(balance))

    def to_string(self):
        return "{id} {name} {wealth}".format(id=self.id, name=self.name, wealth=format_currency(self.wealth))

class Commodity():
    def __init__(self, trade_index, worker, society, depreciation=preferences["default_depreciation"]):
        self.day_created = society.day

        self.trade_index = trade_index
        self.society = society
        #what job makes this
        self.job = self.society.jobs[trade_index]
        self.workers_used = [worker]
        
        self.value = self.get_value()
        self.depreciation_days = depreciation["days"]
        self.percent_salvageable = depreciation["percent"]
        
        self.age = 0

        other_ids = [x.id for x in society.products]
        if not other_ids:
            self.id = 0
        else:
            self.id = max(other_ids) + 1
        self.name = "Thing"

        self.stats = {
            "Workers Required" : self.job.workers_required,
            "Workers" : self.workers_used,
            "Finished" : False
        }

        self.is_finished()

        self.display_objects = [
            Data(name="Value"),
            Data(name="Workers", data=self.stats, display="stats")
        ]

    def depreciate_one_day(self):
        d = self.depreciation_days
        if self.value > self.salvage_value:
            self.value = self.value - (self.value-self.salvage_value) / (d-self.age)
        self.age+=1

    def get_value(self):
        for commodity in self.society.products:
            if commodity.trade_index == self.trade_index:
                return commodity.value
        return 0 #TODO: base this on number of workers used
    def set_value(self, amount):
        self.value = amount
        self.salvage_value = self.value*self.percent_salvageable

    def is_finished(self):
        if self.job.workers_required > len(self.workers_used):
            self.finished = False
        else:
            self.finished = True
        self.stats["Finished"] = self.finished
        return self.finished

    def to_string(self):
        if self.finished:
            f = "Finished"
        else:
            f = "In Production"
        return "{id} {name} {value} {finished}".format(id=self.id, 
                name=self.name, 
                value=format_currency(self.value),
                finished=f)

class Debt(Commodity):
    def __init__(self, society, amount, debtor, creditor, continuous=False, time=30, interest_rate = None):
        
        #######################
        #
        # Commodity Values
        #
        #######################

        self.day_created = society.day

        self.trade_index = -1
        self.society = society
        #what job makes this
        self.job = self.society.jobs[self.trade_index]
        self.workers_used = [] #no labor cost
        
        self.value = amount
        self.depreciation_days = -100 #(200/society.credit_risk) * math.sqrt(debtor.credit_score+society.credit_risk) + 1 #TODO: wth is this? good debt appreciates, bad debt depreciates
        self.salvage_value = 0
        
        self.age = 0

        other_ids = [x.id for x in society.products]
        if not other_ids:
            self.id = 0
        else:
            self.id = max(other_ids) + 1
        self.name = "Debt"



        self.finished = True

        ##################
        #
        # Loan
        #
        ######################


        self.society = society
        self.loan = amount
        self.principle = 0
        self.debtor = debtor
        self.creditor = creditor
        if creditor != None:
            self.creditor.debtors.append(debtor)
            self.creditor.property.append(self)
            self.increase(amount)
        
        self.time = time
        self.last_serviced = self.society.day
        if interest_rate == None:
            self.interest_rate = self.calculate_interest_rate(amount, self.debtor, self.society)
        else:
            self.interest_rate = interest_rate
        
        self.minimum_payment = None
        self.continuous = continuous

        self.society.debts.append(self)

        #######
        #
        # Payment
        #
        #####################

        self.payments = 0

        #####################
        #
        # NonPayment
        #
        #####################

        self.delinquent = False
        self.defaulted = False
        self.days_delinquent = 0
        self.days_defaulted = 0
        self.back_payments = 0.0


        #######################
        #
        #   Display
        #
        #######################

        self.stats = self.__dict__
        #looks like this:
        """
        {
            "Date" : self.society.day,
            "Delinquent" : self.delinquent,
            "Creditor" : creditor,
            "Debtor" : debtor,
            "Principal" : format_currency(amount),
            "Amount" : format_currency(amount),
            "Interest Rate" : self.interest_rate
        }
        """

        self.display_objects = [
            Data(name="Value"),
            Data(name="Stats", data=self.stats, display="stats")
        ]

        self.society.graphs[6].data = np.append(self.society.graphs[6].data, self.interest_rate)

    def update_display_objects(self):
        self.display_objects[0].data = np.append(self.display_objects[0].data, self.value) #single numbers
        self.set_stats()

    def set_stats(self):
        self.stats = self.__dict__
        self.display_objects[-1].data = self.stats #stats always last

    ######################
    #
    #     Actions
    #
    ######################
        
    def calculate_interest_rate(self, amount, person, society, percent_of_income=0.1): #TODO: better deals for bigger loans
        #sd+sd*credit_risk
        if society.credit_score_standard_deviation != 0:
            z = (person.credit_score - society.average_credit_score) / society.credit_score_standard_deviation
        else:
            z = 0
        
        profit = 1.1 #TODO: this could be an interesting var
        x = (1-society.credit_risk*profit)
        if x != 0:
            return_on_investment = amount/(1-society.credit_risk*profit)
            if return_on_investment < 0:
                achievement(2, "\"Credit Crisis!\": Credit Risk is too high! Lenders can't make a profit.")
                self.remove_debt()
                return
        else:
            return

        #get debt to income ratio
        if person.income == 0:
            self.remove_debt()
            return
        income_to_debt_ratio = person.debt / person.income
        #if ratio after applying loan > 0.5: deny loan
        if income_to_debt_ratio > 0.5:
            self.remove_debt()
            return

        #at X percent income
        self.minimum_payment = person.income * percent_of_income
        #how many minimum payments needed to reach return on investment?
        self.expected_payments = return_on_investment / self.minimum_payment
        
        #discount or penalty
        individual_factor = z*society.faith_in_credit_score 


        #TODO: usury laws limit interest (banks will deny even desperate people for loans)

        interest_rate = math.log(return_on_investment/amount)/self.expected_payments - (
            individual_factor / 100 ) #after expected number of minimum payments, what is the profit?

        if interest_rate < society.interest_rate*2:
            #minimum interest rate is double society interest rate
            interest_rate = society.interest_rate*2

        #self.creditor.last_charged_interest += self.interest_rate
        return interest_rate

    def recalculate_minimum_payment(self): #do this before debt is owed at var t
        self.minimum_payment = self.principle / (self.expected_payments)


    def increase(self, amount):
        self.principle += amount
        self.society.consumer_debt += amount
        if self.creditor.cash < amount:
            self.society.log(str(amount))
            self.society.log(str([x.cash for x in self.society.bankers]))
            #This is craziness. The banker can borrow money and loan it to others.
            self.creditor.borrow(amount)
        self.creditor.cash -= amount
        self.debtor.cash += amount
        self.creditor.update_bank_statement(self.society.day, -amount, "Loan to " + str(self.debtor.id), self.creditor.cash)
        self.debtor.update_bank_statement(self.society.day, amount, "Borrowed from " + str(self.creditor.id), self.debtor.cash)
    def decrease(self, amount):
        amount = min(amount, self.principle) #amount can't be bigger than the principle
        amount = min(amount, self.debtor.cash) #amount can't be bigger than cash
        self.principle -= amount
        self.society.consumer_debt -= amount
        self.society.give(self.creditor, amount, self.debtor) #counts as income

        cash_before = self.debtor.cash

        self.debtor.cash -= amount
        if amount >= self.minimum_payment:
            self.debtor.credit_score += preferences["credit"]["credit_score"]["minimum_payment_reward"]
            self.payments+=1
        else:
            self.debtor.credit_score -= preferences["credit"]["credit_score"]["partial_payment_penalty"]
        self.creditor.update_bank_statement(self.society.day, amount, "Debt payment from " + str(self.debtor.id), self.creditor.cash)
        self.debtor.update_bank_statement(self.society.day, -amount, "Debt payment to " + str(self.creditor.id), self.debtor.cash)

        #subtract backpayments and minimum payments
        if self.back_payments > amount:
            self.back_payments -= amount
            amount = 0
        else:
            self.back_payments = 0
            amount -= self.back_payments

        if self.minimum_payment > amount:
            self.minimum_payment -= amount
            amount = 0
        else:
            self.minimum_payment = 0
            amount -= self.minimum_payment

        if self.back_payments == 0 and not self.defaulted:
            if self.delinquent:
                #achievement get
                achievement(1, "\"Clawed My Way Back!\": Someone pulled themselves out of arrears.")
            self.delinquent = False
            self.days_delinquent = 0

        if self.debtor.cash < 0:
            log("WARNING: Negative cash has been created! "+format_currency(cash_before) + "-" + format_currency(amount))
            print()
        if self.principle < 0:
            log("WARNING: Negative debt")
        if self.minimum_payment < 0:
            log("WARNING: Negative minimum payments on a loan")
        if self.back_payments < 0:
            log("WARNING: Negative back payments on a loan")

        self.last_serviced = self.society.day

        #debt is removed by service_debt if principle is 0

    def add_interest(self):
        if self.continuous == True:
            new_principle = self.loan * pow(E, (self.interest_rate*self.age))
            self.society.consumer_debt += new_principle - self.principle
            self.principle = new_principle
        else:
            new_principle = self.loan * pow( 
                (1 + self.interest_rate/self.time), 
                (self.time*self.age)) #TODO: test this
            self.society.consumer_debt += new_principle - self.principle
            self.principle = new_principle

        if self.delinquent:
            self.days_delinquent += 1

        if self.defaulted:
            self.minimum_payment = self.principle
            self.days_defaulted += 1
        elif self.age != 0 and self.age%self.time == 0:
            self.recalculate_minimum_payment()

    def remove_debt(self):
        if self.creditor != None:
            try:
                self.creditor.debtors.remove(self.debtor)
            except ValueError: #TODO: be careful
                pass
            self.creditor.property.remove(self)

        try:
            self.debtor.debts.remove(self)
            achievement(3, "\"Debt Free!\" Someone paid of a loan!")
        except ValueError:
            pass
        

    def delinquency(self, partial_payment):
        self.delinquent = True
        if not self.defaulted:
            self.back_payments += (self.minimum_payment - partial_payment)
        if self.back_payments < 0.0:
            log("Negative: Back payment calculated")
        if partial_payment > 0:
            self.decrease(partial_payment)
            self.debtor.credit_score -= preferences["credit"]["credit_score"]["partial_payment_penalty"]
        else:
            self.debtor.credit_score -= preferences["credit"]["credit_score"]["delinquency_penalty"]

        if self.days_delinquent > 5:
            self.default()
        

        #TODO: fees?
        
    def default(self):
        self.defaulted = True
        self.minimum_payment = self.principle
        self.backpayments = 0 #backpayments should go into the amount owed immediately after default
        self.debtor.credit_score -= preferences["credit"]["credit_score"]["default_penalty"]
        self.debtor.amt_debt_defaulted += self.principle #Used by credit analysts. Never go away. Does not go up with interest

    def set_creditor(self, creditor):
        self.creditor = creditor
        self.creditor.debtors.append(self.debtor)
        if self.principle == 0:
            self.increase(self.loan)
        creditor.property.append(self)
        self.society.debts.append(self)

    def to_string(self):
        return "{debtor} owes {amount} to {creditor} at {interest} interest".format(
            debtor=self.debtor.id, 
            amount=format_currency(self.principle), 
            creditor=self.creditor.id,
            interest=str(self.interest_rate*100)+"%")

#TODO: class Good(): #types of goods that exist and their average price
#TODO: class Service(): #types of services that exist and their average price
#TODO: class Company(): #represents an owner or co-owners who take money out of wages

class Job():
    #Each job produces a product, and requires different numbers of workers
    def __init__(self, index, society):
        self.index = index
        workers_required = 1
        #Half of the jobs reqire 1 person. Half require 2 or more.
        for n in range(society.max_employees):
            if random.randint(0,1):
                break
            workers_required += 1

        self.workers_required = workers_required
        self.name = "Laborer"

        other_ids = [x.id for x in society.jobs]
        if not other_ids:
            self.id = 0
        else:
            self.id = max(other_ids) + 1

        self.wage = 0.0

        self.display_objects = [
            Data(name="Wage"),
            Data(name="Products")
        ]

    def to_string(self):
        return "{id} {name} {wage}".format(id=self.id, name=self.name, wage=format_currency(self.wage)+"/hr")

#TODO: class Industries() How many employed / how many available in each career?

def format_currency(f):
    if CURRENCY_FORMAT == 'custom':
        return "?"
    else:
        return locale.currency(f)

def elapse_one_day(society):
    society.update()
    society.day+=1

#################################
#
#      Inequality functions
#
#################################

def gini(arr):
   ## first sort
    arr = np.array(arr)
    sorted_arr = arr.copy()
    sorted_arr.sort()
    n = arr.size
    coef_ = 2. / n
    const_ = (n + 1.) / n
    weighted_sum = sum([(i+1)*yi for i, yi in enumerate(sorted_arr)])
    return coef_*weighted_sum/(sorted_arr.sum()) - const_
def lorenz_curve(arr):
    X = np.array(arr)
    X.sort()
    X_lorenz = X.cumsum() / X.sum()
    X_lorenz = np.insert(X_lorenz, 0, 0)
    X_lorenz[0], X_lorenz[-1]
    return X_lorenz

def get_sigma(values, mean, population_size):
     return math.sqrt(
         sum([(s-mean)**2 for s in values])**2 / population_size) #TODO:make var for some len() calculations

#########################
#
#   Logging
#
#########################

def log(message):
    log_message = message
    with open(logfile, 'a') as l:
        l.write(str(log_message)+"\n")
    if preferences["print_logs"] == True:
        print(log_message)

def achievement(id, text):
    if id not in achievements:
        with open("achievements.txt", 'a') as l:
            l.write(str(text)+"\n")
        achievements.append(id)
        if preferences["print_achievements"] == True:
            print(text)

def clear_logs():
    with open(logfile, 'w') as l:
        l.write("")

def clear_achievements():
    with open("achievements.txt", 'w') as l:
        l.write("")
    global achievements
    achievements = []

#########################
#
#   Main Program
#
#########################


#TODO: create settings file
if __name__ == "__main__":

    population = input("How big is your population? (100)") #TODO: get defaults from settings file
    if not population:
        population = 100
    else:
        population = int(population)
    money_reserves = input("How much money will you print? (1000000)")
    if not money_reserves:
        money_reserves = 1000000
    else:
        money_reserves = int(money_reserves)
    days = input("How many days will you measure? (100)")
    if not days:
        days = 100
    else:
        days = int(days)

    society = Society(population, money_reserves)

    for day in range(days):
        elapse_one_day(society)
