average_price = 35
in_range = 0.52
.27

capital = 100

import random
import pandas as pd
import matplotlib.pyplot as plt


random.uniform(0,1)
def tester():
    res = []
    capital = 100
    for i in range(100):
        val = random.uniform(0,1)
        if val < 0.52:
            percent_return = 100/35
            capital = capital - 0.27*capital + (0.27*capital)*percent_return
        else:
            capital = capital - 0.27*capital
        res.append(capital)
    return res, capital


results = []
end_capital = []
for i in range(1000):
    test = tester()
    results.append(test[0])
    end_capital.append(test[1])
    


plt.hist(end_capital,bins=[0, 10, 50, 100, 200, 500, 1000, 10000, 100000],edgecolor='k')
plt.xscale("log")


plt.show()

# print(sum([i[-1] for i in results])/10000)

# plt.scatter([i for i in range(10000)], [i[-1] for i in results])
    
plt.figure()

for i, sublist in enumerate(results):
    plt.plot(sublist, color='red')


    
plt.show()
    


# def tester():
#     capital = 1000
#     for i in range(100):
#         val = random.uniform(0,1)
#         if val < 0.47:
#             percent_return = 100/40
#             capital = capital - capital/5 + (capital/5)*percent_return
#         else:
#             capital = capital - capital/5
#     return capital

# results = []
# for i in range(1000):
#     result = tester()
#     print(result)
#     results.append(result)
    
# print(sum(results)/len(results))

    