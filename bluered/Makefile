CC = "C:\Program Files\mingw64\bin\gcc.exe"
CFLAGS = -Wall -Wextra -O2 -mwindows -msse2 -mconsole
LDFLAGS = -lws2_32 -ladvapi32 -lshell32

# Directories
INCLUDE_DIR = include
SRC_DIR = src

# Source Files
SOURCES = \
    $(SRC_DIR)/main.c \
    $(SRC_DIR)/exploit.c \
    $(SRC_DIR)/persistence.c \
    $(SRC_DIR)/backdoor.c \
    $(SRC_DIR)/winsock_admin.c

# Object Files (explicitly list all 5 .o files)
MAIN_OBJ = $(SRC_DIR)/main.o
EXPLOIT_OBJ = $(SRC_DIR)/exploit.o
PERSISTENCE_OBJ = $(SRC_DIR)/persistence.o
BACKDOOR_OBJ = $(SRC_DIR)/backdoor.o
WINSOCK_ADMIN_OBJ = $(SRC_DIR)/winsock_admin.o

OBJECTS = $(MAIN_OBJ) $(EXPLOIT_OBJ) $(PERSISTENCE_OBJ) $(BACKDOOR_OBJ) $(WINSOCK_ADMIN_OBJ)
TARGET = $(SRC_DIR)/BlueRed.exe

# Default target
.PHONY: all clean recompile run

all: $(TARGET)

$(TARGET): $(MAIN_OBJ) $(EXPLOIT_OBJ) $(PERSISTENCE_OBJ) $(BACKDOOR_OBJ) $(WINSOCK_ADMIN_OBJ)
	$(CC) $(CFLAGS) -o $(TARGET) $(MAIN_OBJ) $(EXPLOIT_OBJ) $(PERSISTENCE_OBJ) $(BACKDOOR_OBJ) $(WINSOCK_ADMIN_OBJ) $(LDFLAGS)

# Build all object files
$(MAIN_OBJ): $(SRC_DIR)/main.c $(INCLUDE_DIR)/config.h $(INCLUDE_DIR)/types.h $(INCLUDE_DIR)/winsock_admin.h
	$(CC) $(CFLAGS) -I$(INCLUDE_DIR) -I$(SRC_DIR) -c $(SRC_DIR)/main.c -o $(MAIN_OBJ)

$(EXPLOIT_OBJ): $(SRC_DIR)/exploit.c $(INCLUDE_DIR)/config.h $(INCLUDE_DIR)/types.h
	$(CC) $(CFLAGS) -I$(INCLUDE_DIR) -I$(SRC_DIR) -c $(SRC_DIR)/exploit.c -o $(EXPLOIT_OBJ)

$(PERSISTENCE_OBJ): $(SRC_DIR)/persistence.c $(INCLUDE_DIR)/config.h $(INCLUDE_DIR)/types.h
	$(CC) $(CFLAGS) -I$(INCLUDE_DIR) -I$(SRC_DIR) -c $(SRC_DIR)/persistence.c -o $(PERSISTENCE_OBJ)

$(BACKDOOR_OBJ): $(SRC_DIR)/backdoor.c $(INCLUDE_DIR)/config.h $(INCLUDE_DIR)/types.h
	$(CC) $(CFLAGS) -I$(INCLUDE_DIR) -I$(SRC_DIR) -c $(SRC_DIR)/backdoor.c -o $(BACKDOOR_OBJ)

$(WINSOCK_ADMIN_OBJ): $(SRC_DIR)/winsock_admin.c $(INCLUDE_DIR)/config.h $(INCLUDE_DIR)/types.h $(INCLUDE_DIR)/winsock_admin.h
	$(CC) $(CFLAGS) -I$(INCLUDE_DIR) -I$(SRC_DIR) -c $(SRC_DIR)/winsock_admin.c -o $(WINSOCK_ADMIN_OBJ)

clean:
	rm -f $(MAIN_OBJ) $(EXPLOIT_OBJ) $(PERSISTENCE_OBJ) $(BACKDOOR_OBJ) $(WINSOCK_ADMIN_OBJ) $(TARGET)

recompile: clean all

run: $(TARGET)
	$(TARGET)