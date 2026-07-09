### Operation done by python memory manager
1. my_var = ObjectA
2. ObjectA has a variable which is pointing to ObjectB
3. so when we assing my_var to something else like my_var=None
4. then refrence count of ObjectA goes to 0 so ObjectA is destroyed
5. as ObjectA is destroyed then refrence count of ObjectB also get 0
6. so ObjectB is also gets destroyed


### circular refrence
1. my_var = ObjectA
2. ObjectA has a variable which is pointing to ObjectB
3. ObjectB has a variable which is pointing to ObjectA
4. then refrence count of ObjectA will be 2 and refrence count of ObjectB will be 1
5. so when my_var is assigned to something else like my_var = None
6. then refrence count of ObjectA will be 1 and refrence count of ObjectB will be 1 also
7. also there is no way to reach ObjectA also ObjectA's refrence count will be 1 always then after
8. so python memory manager will not able to claim that space so memory leak will happen

- to solve this issue

### garbage collector
1. can be controlled programmatically using gc module
2. by default it is turned on
3. you may turn it off.
4. runs periodically on its own (it turned on)
5. you can call it manually, and even do your own cleanup
