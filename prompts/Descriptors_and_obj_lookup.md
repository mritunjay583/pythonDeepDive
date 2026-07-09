# Objective

Act as a CPython core developer and Python object model expert.

Create an advanced systems-level document explaining descriptors, attribute lookup, bound methods, metaclasses, and Python's object model internals.

Assume I already understand:

* Object Model
* Memory Management
* Bytecode
* PVM
* Dictionaries

---

# Topics

## Attribute Lookup

Teach:

obj.attr

Exactly what happens internally.

Step-by-step.

Include:

instance dictionary

class dictionary

MRO

Inheritance

**dict**

**slots**

Memory diagrams.

---

## Descriptors

Teach:

Data descriptors

Non-data descriptors

property

classmethod

staticmethod

Functions as descriptors

Bound methods

Method objects

Descriptor protocol

**get**

**set**

**delete**

Why descriptors exist.

---

## Method Resolution Order

Explain:

C3 Linearization

Diamond inheritance

super()

Implementation.

---

## Metaclasses

Teach:

type

Metaclass creation

Class construction

**new**

**init**

Custom metaclasses

---

## **getattribute**

**getattr**

Lookup order

Customization

Performance implications

---

## CPython Source

Objects/typeobject.c

Objects/descrobject.c

Objects/object.c

Walk through important functions.

---

## Interview

50 Beginner

50 Intermediate

50 Senior

100 attribute lookup prediction problems
