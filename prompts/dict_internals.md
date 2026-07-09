# Objective

Act as a CPython core developer and systems programming professor.

Create a complete production-quality document teaching Dictionary and Set internals from first principles.

The goal is to understand why Python dictionaries are among the fastest hash tables ever implemented and how modern CPython stores dictionaries in memory.

Assume I already understand:

* Python Object Model
* References
* PyObject
* PyVarObject
* Lists Internals
* PyMalloc

---

# Topics

Cover in extreme depth:

## Hash Tables

* Why arrays fail
* Why linked lists fail
* Hash tables
* Load factor
* Buckets
* Collisions

---

## Hash Functions

Explain:

hash()

SipHash

Security

Hash randomization

Collision attacks

---

## PyDictObject

Explain every field.

Memory layout.

Combined table

Split table

Key-sharing dictionaries

Why class instances save memory.

---

## Lookup Algorithm

Step-by-step.

Probe sequence.

Open addressing.

Perturb algorithm.

Deleted entries.

Dummy markers.

Why lookup is O(1).

Worst case.

---

## Insert

Delete

Resize

Growth strategy

Shrink strategy

Memory diagrams.

---

## Dictionaries after Python 3.6

Compact dictionaries

Insertion ordering

Why ordering became guaranteed in Python 3.7

Historical evolution.

---

## Sets

Explain how sets reuse dictionary concepts.

Differences.

Membership testing.

Union

Intersection

Difference

Complexity.

---

## Hashability

Why immutable objects are hashable.

Why lists are not.

**hash**

**eq**

Custom objects.

Frozen dataclasses.

---

## CPython Source

Objects/dictobject.c

Important functions.

Walk through source.

---

## Performance

Cache locality

Memory usage

Large dictionaries

Millions of keys

Production optimizations

---

## Interview

50 beginner

50 intermediate

50 senior

100 coding questions

Memory diagrams

Exercises
