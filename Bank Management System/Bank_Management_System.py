import os

DATA_FILE = "bankAccount.txt"


class BankAccount:
    def __init__(self, name="", account_number="", balance=0.0):
        self.name = name
        self.account_number = account_number
        self.balance = balance

    def get_account_number(self):
        return self.account_number

    def create_account(self):
        while True:
            self.name = input("\nEnter customer name: ").strip()
            if self.name:
                break
            print("Name cannot be empty.")

        while True:
            self.account_number = input("Enter account number: ").strip()
            if self.account_number:
                break
            print("Account number cannot be empty.")

        self.balance = 0.0
        print("\nAccount created successfully!")

    def show_details(self):
        print("\n-----------------------------")
        print(f"Customer Name : {self.name}")
        print(f"Account Number: {self.account_number}")
        print(f"Balance       : ₹{self.balance:.2f}")
        print("-----------------------------")

    def show_balance(self):
        print(f"\nAccount Number : {self.account_number}")
        print(f"Current Balance: ₹{self.balance:.2f}")

    def _read_amount(self, prompt):
        try:
            amount = float(input(prompt))
        except ValueError:
            print("Invalid amount.")
            return None
        if amount <= 0:
            print("Enter a valid amount.")
            return None
        return amount

    def deposit(self):
        amount = self._read_amount("\nEnter amount to deposit: ₹")
        if amount is None:
            return
        self.balance += amount
        print("Amount deposited successfully.")
        self.show_balance()

    def withdraw(self):
        amount = self._read_amount("\nEnter amount to withdraw: ₹")
        if amount is None:
            return
        if amount > self.balance:
            print("Insufficient balance.")
            return
        self.balance -= amount
        print("Amount withdrawn successfully.")
        self.show_balance()

    def to_line(self):
        return f"{self.name}|{self.account_number}|{self.balance}\n"


def save_all_accounts(accounts):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            for acc in accounts:
                f.write(acc.to_line())
    except OSError:
        print("Error saving account data.")


def load_all_accounts():
    accounts = []
    if not os.path.exists(DATA_FILE):
        return accounts

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("|")
            if len(parts) != 3:
                continue
            try:
                accounts.append(BankAccount(parts[0], parts[1], float(parts[2])))
            except ValueError:
                continue
    return accounts


def find_account(accounts, account_number):
    for i, acc in enumerate(accounts):
        if acc.get_account_number() == account_number:
            return i
    return -1


def prompt_account(accounts):
    number = input("\nEnter account number: ").strip()
    index = find_account(accounts, number)
    if index == -1:
        print("Account not found.")
    return index


def main():
    accounts = load_all_accounts()

    while True:
        print("\n============================================")
        print("          BANK MANAGEMENT SYSTEM")
        print("============================================")
        print("1. Create New Account")
        print("2. Show All Accounts")
        print("3. Search Account")
        print("4. Deposit Money")
        print("5. Withdraw Money")
        print("6. Check Balance")
        print("7. Exit")
        print("============================================")

        try:
            choice = int(input("Enter your choice: "))
        except ValueError:
            print("Invalid choice. Please try again.")
            continue

        if choice == 1:
            new_account = BankAccount()
            new_account.create_account()
            if find_account(accounts, new_account.get_account_number()) != -1:
                print("Account number already exists.")
            else:
                accounts.append(new_account)
                save_all_accounts(accounts)
                print("Account saved successfully.")

        elif choice == 2:
            if not accounts:
                print("\nNo accounts found.")
            else:
                print("\n========== ALL ACCOUNTS ==========")
                for acc in accounts:
                    acc.show_details()

        elif choice == 3:
            index = prompt_account(accounts)
            if index != -1:
                accounts[index].show_details()

        elif choice == 4:
            index = prompt_account(accounts)
            if index != -1:
                accounts[index].deposit()
                save_all_accounts(accounts)

        elif choice == 5:
            index = prompt_account(accounts)
            if index != -1:
                accounts[index].withdraw()
                save_all_accounts(accounts)

        elif choice == 6:
            index = prompt_account(accounts)
            if index != -1:
                accounts[index].show_balance()

        elif choice == 7:
            print("\nThank you for using the Bank Management System!")
            break

        else:
            print("Enter a valid choice.")


if __name__ == "__main__":
    main()
