import os

FILE_NAME = "studentRecord.txt"


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def read_records():
    """Return a list of [id, name, age, course] from the file."""
    records = []
    if not os.path.exists(FILE_NAME):
        return records
    with open(FILE_NAME, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("|", 3)
            if len(parts) == 4:
                records.append(parts)
    return records


def write_records(records):
    with open(FILE_NAME, "w", encoding="utf-8") as f:
        for r in records:
            f.write("|".join(r) + "\n")


def print_record(r):
    print(f"\nStudent ID     : {r[0]}")
    print(f"Student Name   : {r[1]}")
    print(f"Student Age    : {r[2]}")
    print(f"Student Course : {r[3]}")


def ask(prompt):
    """Ask until the input is non-empty and has no '|' in it."""
    while True:
        value = input(prompt).strip()
        if value and "|" not in value:
            return value
        print("Input can't be empty or contain '|'.")


def read_age(prompt):
    while True:
        value = input(prompt).strip()
        if value.isdigit():
            return value
        print("Please enter a valid number.")


class Student:
    def menu(self):
        while True:
            clear()
            print("-----------------------------------------")
            print("|      STUDENT MANAGEMENT SYSTEM       |")
            print("-----------------------------------------")
            print("1. Enter New Record")
            print("2. Display Record")
            print("3. Update Record")
            print("4. Search Record")
            print("5. Delete Record")
            print("6. Exit")
            print("-----------------------------------------")

            choice = input("Enter Your Choice: ").strip()

            if choice == "1":
                while True:
                    self.insert()
                    again = input("\nAdd Another Student Record (Y/N): ")
                    if again.lower() != "y":
                        break
            elif choice == "2":
                self.display()
            elif choice == "3":
                self.update()
            elif choice == "4":
                self.search()
            elif choice == "5":
                self.delete_record()
            elif choice == "6":
                print("\nThank you for using Student Management System.")
                break
            else:
                print("\nInvalid choice. Please try again.")

            input("\n\nPress Enter to continue...")

    def insert(self):
        clear()
        print("\n------------- Add Student Details -------------")
        sid = ask("Enter Student ID: ")

        if any(r[0] == sid for r in read_records()):
            print("\nA student with this ID already exists.")
            return

        name = ask("Enter Student Name: ")
        age = read_age("Enter Student Age: ")
        course = ask("Enter Student Course: ")

        with open(FILE_NAME, "a", encoding="utf-8") as f:
            f.write(f"{sid}|{name}|{age}|{course}\n")

        print("\nStudent record added successfully!")

    def display(self):
        clear()
        print("\n------------- Student Records -------------")
        records = read_records()
        if not records:
            print("\nNo records found.")
            return
        for r in records:
            print_record(r)
            print("---------------------------------------------")

    def search(self):
        clear()
        print("\n------------- Search Student -------------")
        search_id = input("Enter Student ID: ").strip()

        for r in read_records():
            if r[0] == search_id:
                print("\nStudent Found!")
                print_record(r)
                return
        print("\nStudent record not found.")

    def update(self):
        clear()
        print("\n------------- Update Student -------------")
        update_id = input("Enter Student ID: ").strip()

        records = read_records()
        found = False

        for r in records:
            if r[0] == update_id:
                r[1] = ask("\nEnter New Name: ")
                r[2] = read_age("Enter New Age: ")
                r[3] = ask("Enter New Course: ")
                found = True
                break

        if found:
            write_records(records)
            print("\nStudent record updated successfully!")
        else:
            print("\nStudent record not found.")

    def delete_record(self):
        clear()
        print("\n------------- Delete Student -------------")
        delete_id = input("Enter Student ID: ").strip()

        records = read_records()
        remaining = [r for r in records if r[0] != delete_id]

        if len(remaining) != len(records):
            write_records(remaining)
            print("\nStudent record deleted successfully!")
        else:
            print("\nStudent record not found.")


if __name__ == "__main__":
    Student().menu()
