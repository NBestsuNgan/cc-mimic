def show_menu():
    print("=" * 35)
    print("       Welcome to Hello Program      ")
    print("=" * 35)
    print("  1. Enter your name")
    print("  2. Choose greeting style")
    print("  3. Show greeting")
    print("  4. Exit")
    print("=" * 35)


def get_name():
    name = input("Enter your name: ").strip()
    if name:
        print(f"  >> Name set to: {name}")
    else:
        print("  >> Name cannot be empty.")
    return name


def choose_style():
    print("\n  Greeting Styles:")
    print("  1. Casual  - Hey there!")
    print("  2. Formal  - Good day.")
    print("  3. Fun     - What's up?!")
    choice = input("  Choose a style (1-3): ").strip()
    styles = {
        "1": "Hey there",
        "2": "Good day",
        "3": "What's up",
    }
    style = styles.get(choice)
    if style:
        print(f"  >> Style set to: {style}")
    else:
        print("  >> Invalid choice. Defaulting to Casual.")
        style = "Hey there"
    return style


def show_greeting(name, style):
    if not name:
        print("\n  >> Please enter your name first (option 1).")
        return
    if not style:
        style = "Hey there"
    print("\n" + "-" * 35)
    print(f"  {style}, {name}!")
    print("-" * 35 + "\n")


def main():
    name = ""
    style = None

    while True:
        show_menu()
        choice = input("Select an option (1-4): ").strip()
        print()

        if choice == "1":
            result = get_name()
            if result:
                name = result
        elif choice == "2":
            if not name:
                print("  >> Please enter your name first (option 1).")
            else:
                style = choose_style()
        elif choice == "3":
            show_greeting(name, style)
        elif choice == "4":
            print("Goodbye!\n")
            break
        else:
            print("  >> Invalid option. Please choose 1-4.\n")


if __name__ == "__main__":
    main()
