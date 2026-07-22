"""
Tiny CPU Simulator
==================
Phase 0 Project — Build a simple CPU that demonstrates the Fetch-Decode-Execute cycle.

YOUR TASK: Fill in the TODO sections to make this work.

Instruction Set:
    MOV   Rd, value       — Rd = value (load immediate)
    ADD   Rd, Rs1, Rs2    — Rd = Rs1 + Rs2
    SUB   Rd, Rs1, Rs2    — Rd = Rs1 - Rs2
    LOAD  Rd, addr        — Rd = memory[addr]
    STORE addr, Rs        — memory[addr] = Rs
    JMP   addr            — PC = addr (unconditional jump)
    JZ    addr            — if zero_flag: PC = addr (jump if zero)
    HALT                  — stop execution

Registers: R0-R7 (8 general purpose)
Memory: 256 slots
"""


class CPU:
    def __init__(self):
        self.registers = [0] * 8       # R0 - R7
        self.pc = 0                     # Program Counter
        self.zero_flag = False          # Set when last arithmetic result == 0
        self.memory = [None] * 256      # Instruction + Data memory
        self.halted = False
        self.cycle_count = 0

    def load_program(self, program):
        """Load a list of instruction tuples into memory starting at address 0."""
        for i, instruction in enumerate(program):
            self.memory[i] = instruction

    # ─────────────────────────────────────────────
    # STAGE 1: FETCH
    # ─────────────────────────────────────────────
    def fetch(self):
        """
        TODO:
        1. Read the instruction at memory[self.pc]
        2. Increment self.pc by 1
        3. Return the instruction
        """
        pass

    # ─────────────────────────────────────────────
    # STAGE 2: DECODE
    # ─────────────────────────────────────────────
    def decode(self, instruction):
        """
        TODO:
        1. Extract the opcode (first element of the tuple)
        2. Extract the operands (remaining elements)
        3. Return (opcode, operands)

        Example:
            instruction = ("ADD", 2, 0, 1)
            → opcode = "ADD", operands = (2, 0, 1)
        """
        pass

    # ─────────────────────────────────────────────
    # STAGE 3: EXECUTE
    # ─────────────────────────────────────────────
    def execute(self, opcode, operands):
        """
        TODO: Implement each instruction.

        MOV:   operands = (Rd, value)
               → self.registers[Rd] = value

        ADD:   operands = (Rd, Rs1, Rs2)
               → self.registers[Rd] = self.registers[Rs1] + self.registers[Rs2]
               → update zero_flag

        SUB:   operands = (Rd, Rs1, Rs2)
               → self.registers[Rd] = self.registers[Rs1] - self.registers[Rs2]
               → update zero_flag

        LOAD:  operands = (Rd, addr)
               → self.registers[Rd] = self.memory[addr]

        STORE: operands = (addr, Rs)
               → self.memory[addr] = self.registers[Rs]

        JMP:   operands = (addr,)
               → self.pc = addr

        JZ:    operands = (addr,)
               → if self.zero_flag: self.pc = addr

        HALT:  operands = ()
               → self.halted = True

        HINT: Use if/elif chain. Don't forget to update self.zero_flag
              after ADD and SUB (flag = True if result == 0).
        """
        pass

    # ─────────────────────────────────────────────
    # THE MAIN LOOP: Fetch → Decode → Execute
    # ─────────────────────────────────────────────
    def run(self):
        """Run the CPU until HALT instruction."""
        print("=" * 50)
        print("CPU Starting...")
        print("=" * 50)

        while not self.halted:
            # Fetch
            instruction = self.fetch()

            # Decode
            opcode, operands = self.decode(instruction)

            # Execute
            self.execute(opcode, operands)

            # Track cycles
            self.cycle_count += 1

            # Print state after each cycle
            self.print_state(opcode, operands)

        print("=" * 50)
        print(f"CPU Halted after {self.cycle_count} cycles.")
        print(f"Final registers: {self.registers}")
        print("=" * 50)

    def print_state(self, opcode, operands):
        """Print the CPU state after each cycle."""
        regs = " ".join(f"R{i}={v}" for i, v in enumerate(self.registers) if v != 0)
        if not regs:
            regs = "R0=0"
        print(f"  Cycle {self.cycle_count:3d} | {opcode:5s} {str(operands):12s} | "
              f"PC={self.pc:3d} | {regs} | zero={self.zero_flag}")


# ═══════════════════════════════════════════════════
# TEST PROGRAMS — Run these after you implement CPU
# ═══════════════════════════════════════════════════

def test_1_basic_addition():
    """Test: 5 + 3 = 8"""
    print("\n>>> Test 1: Basic Addition (5 + 3)")
    program = [
        ("MOV", 0, 5),         # R0 = 5
        ("MOV", 1, 3),         # R1 = 3
        ("ADD", 2, 0, 1),      # R2 = R0 + R1 = 8
        ("HALT",),
    ]
    cpu = CPU()
    cpu.load_program(program)
    cpu.run()
    assert cpu.registers[2] == 8, f"Expected R2=8, got R2={cpu.registers[2]}"
    print("✓ PASSED\n")


def test_2_subtraction():
    """Test: 10 - 4 = 6"""
    print("\n>>> Test 2: Subtraction (10 - 4)")
    program = [
        ("MOV", 0, 10),        # R0 = 10
        ("MOV", 1, 4),         # R1 = 4
        ("SUB", 2, 0, 1),      # R2 = R0 - R1 = 6
        ("HALT",),
    ]
    cpu = CPU()
    cpu.load_program(program)
    cpu.run()
    assert cpu.registers[2] == 6, f"Expected R2=6, got R2={cpu.registers[2]}"
    print("✓ PASSED\n")


def test_3_countdown_loop():
    """Test: Countdown from 5 to 0 using a loop (tests JZ + JMP)"""
    print("\n>>> Test 3: Countdown Loop (5 → 0)")
    program = [
        ("MOV", 0, 5),         # R0 = 5 (counter)
        ("MOV", 1, 1),         # R1 = 1 (decrement value)
        # --- loop starts at address 2 ---
        ("SUB", 0, 0, 1),      # R0 = R0 - 1  [addr 2]
        ("JZ", 5),             # if R0 == 0, jump to HALT (addr 5)  [addr 3]
        ("JMP", 2),            # else jump back to loop start  [addr 4]
        # --- loop ends ---
        ("HALT",),             # [addr 5]
    ]
    cpu = CPU()
    cpu.load_program(program)
    cpu.run()
    assert cpu.registers[0] == 0, f"Expected R0=0, got R0={cpu.registers[0]}"
    print("✓ PASSED\n")


def test_4_sum_1_to_5():
    """
    Test: Compute 1+2+3+4+5 = 15 using a loop.

    Logic:
        R0 = counter (starts at 5)
        R1 = 1 (for decrementing)
        R2 = sum (accumulator)

    Loop:
        sum += counter
        counter -= 1
        if counter == 0: halt
        else: loop
    """
    print("\n>>> Test 4: Sum 1 to 5 (= 15)")
    program = [
        ("MOV", 0, 5),         # R0 = 5 (counter)
        ("MOV", 1, 1),         # R1 = 1 (decrement value)
        ("MOV", 2, 0),         # R2 = 0 (sum)
        # --- loop starts at address 3 ---
        ("ADD", 2, 2, 0),      # R2 = R2 + R0 (sum += counter)  [addr 3]
        ("SUB", 0, 0, 1),      # R0 = R0 - 1  [addr 4]
        ("JZ", 7),             # if R0 == 0, jump to HALT  [addr 5]
        ("JMP", 3),            # else jump back to loop  [addr 6]
        # --- loop ends ---
        ("HALT",),             # [addr 7]
    ]
    cpu = CPU()
    cpu.load_program(program)
    cpu.run()
    assert cpu.registers[2] == 15, f"Expected R2=15, got R2={cpu.registers[2]}"
    print("✓ PASSED\n")


def test_5_load_store():
    """Test: Store a value to memory, load it back"""
    print("\n>>> Test 5: Load/Store Memory")
    program = [
        ("MOV", 0, 42),        # R0 = 42
        ("STORE", 100, 0),     # memory[100] = R0 (store 42 at address 100)
        ("MOV", 0, 0),         # R0 = 0 (clear it)
        ("LOAD", 1, 100),      # R1 = memory[100] (should be 42)
        ("HALT",),
    ]
    cpu = CPU()
    cpu.load_program(program)
    cpu.run()
    assert cpu.registers[1] == 42, f"Expected R1=42, got R1={cpu.registers[1]}"
    print("✓ PASSED\n")


# ═══════════════════════════════════════════════════
# RUN ALL TESTS
# ═══════════════════════════════════════════════════

if __name__ == "__main__":
    test_1_basic_addition()
    test_2_subtraction()
    test_3_countdown_loop()
    test_4_sum_1_to_5()
    test_5_load_store()
    print("🎉 All tests passed! Your CPU works.")
