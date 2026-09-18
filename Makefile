SRC = utils/native/dice.zig
TARGET = utils/native/libdice.so

all: $(TARGET)

$(TARGET): $(SRC)
	zig build-lib $(SRC) -dynamic -O ReleaseFast -femit-bin=$(TARGET)

clean:
	rm -f $(TARGET)
