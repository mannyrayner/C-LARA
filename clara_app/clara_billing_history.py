def print_total_paid(filename='c:/cygwin64/home/mannyrayner/billing.txt'):
    # Specify the filename with your billing history
    total_paid = calculate_total(filename)
    print(f"Total amount paid: ${total_paid:.2f}")

def calculate_total(filename):
    total = 0.0
    
    with open(filename, 'r') as file:
        for line in file:
            # Split the line into parts
            parts = line.split()
            # Find the amount by looking for the part that starts with '$'
            for part in parts:
                if part.startswith('$'):
                    # Remove the '$' and convert the rest to a float
                    amount = float(part[1:])
                    total += amount
                    break

    return total

