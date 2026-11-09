# Student Management System

A Python-based Student Management System that uses Object-Oriented Programming (OOP) and file handling to manage student records from the command line.

## Features

- Add new student records
- Display all student records
- Search for a student by ID
- Update student information
- Delete student records
- Prevents duplicate student IDs
- Input validation (no empty fields, numeric age, no `|` character)
- Store student data using file handling

## Technologies Used

- Python 3
- Object-Oriented Programming (OOP)
- File Handling
- Lists and list comprehensions
- `os` module

## How to Run

1. Make sure Python 3 is installed:
   ```bash
   python --version
   ```
2. Run the program:
   ```bash
   python student_management_v2.py
   ```
3. Use the menu to add, display, search, update, or delete student records.

## Data Storage

Student records are stored locally in `studentRecord.txt`, one record per line in this format:

```
id|name|age|course
```

The data file is excluded from this repository using `.gitignore`.
