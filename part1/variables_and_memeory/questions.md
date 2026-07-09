## Language building blocks

1. how to store information in a language. (variables)
    1. dynamic typing, 
    2. static typing : variable types
    3. constants
    4. mutability and immutability
    5. refrences
    6. how to compare variables
    7. when information gets memory and who refrences it
2. how memory is managed in the language. (what any language does to cleanup the unsed memory)
    1. auto memory cleanup (like python memory manager, and other memory managers)
    2. garbage collectors (memory freeing technique when lanageuage memory manager does not able to do it self)



1. variables are nothing but just memory refrences

2. so memory is nothing but just slots. and each slots has unique address. information can take one or more than one contigious slots to store.and knowing the starting address of the information we can access the information.


3. removing and storing object in heap memory done by python memory manager
4. variables in python is just refrences of the object at address X.
    -   so if you write my_var = 10 then object 10 is created at address x. and my_var will be pointing to address x. not 10 directly
    - so when you write statement like var = "something" then first something is created in heap and address of that stored in var.
    - we can find out the memory address refrenced by a variable by using the id() function
    - this will return a base-10 number. we can convert this base-10 number to hexadecimal, by using hex() function
    - eg: a=10
            print(hex(id(a)))

5. in python when we write
    -   var = 10
    - then these are done
        1. object of value 10 is created in memory
        2. a pointer named var is also created in memory
        3. address of object valued 10 is stored in var pointer
        4. refrence table got updated
            - refernce = address of the object valued 10
            - count = 1
