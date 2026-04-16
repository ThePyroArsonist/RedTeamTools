CC = "C:\Program Files\mingw64\bin\gcc.exe"
CFLAGS = -Wall -Wextra -O2 -mwindows -msse2 -mconsole
LDFLAGS = -lws2_32 -ladvapi32 -lshell32

# Directories
INCLUDE_DIR = include
SRC_DIR = src

# Source Files - UPDATED
SOURCES = \
    $(SRC_DIR)/main.c \
    $(SRC_DIR)/exploit.c \
    $(SRC_DIR)/persistence.c \
    $(SRC_DIR)/backdoor.c \
    $(SRC_DIR)/winsock_admin.c 

OBJECTS = $(SOURCES:.c=.o)
TARGET = $(SRC_DIR)/BlueRedExe.exe

# Default target
.PHONY: all clean recompile run

all: $(TARGET)

$(TARGET): $(OBJECTS)
	$(CC) $(CFLAGS) -o $(TARGET) $(OBJECTS) $(LDFLAGS)

%.o: %.c include/config.h include/winsock_admin.h
	$(CC) $(CFLAGS) $(INCLUDES) -I$(INCLUDE_DIR) -I$(SRC_DIR) -c $< -o $@

clean:
	rm -f $(OBJECTS) $(TARGET)

recompile: clean all

run: $(TARGET)
	$(TARGET)
