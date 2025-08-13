/**
 * Sample Go file to test tree-sitter-go analysis
 * This file contains Go-specific patterns and potential issues
 */

package main

import (
	"database/sql"
	"fmt"
	"log"
	"os"
	"os/exec"
	"strings"
)

// Security issue - hardcoded credentials
const (
	API_KEY    = "go-api-key-123456789" // BAD: Hardcoded secret
	DB_PASSWORD = "supersecret123"       // BAD: Hardcoded password
)

// Large struct that might need refactoring
type UserManager struct {
	users       map[int]User
	connections []string
	config      Config
	cache       map[string]interface{}
	logger      *log.Logger
	db          *sql.DB
}

type User struct {
	ID       int    `json:"id"`
	Name     string `json:"name"`
	Email    string `json:"email"`
	IsActive bool   `json:"is_active"`
}

type Config struct {
	Timeout int
	Retries int
	Host    string
}

// Function with SQL injection vulnerability
func (um *UserManager) GetUserByName(name string) (*User, error) {
	// BAD: String concatenation in SQL query
	query := fmt.Sprintf("SELECT * FROM users WHERE name = '%s'", name)
	return um.executeQuery(query)
}

// Function with command injection vulnerability
func (um *UserManager) ExecuteCommand(userInput string) error {
	// BAD: Unsanitized user input in system command
	cmd := exec.Command("sh", "-c", fmt.Sprintf("ls -la %s", userInput))
	_, err := cmd.Output()
	return err
}

// Complex function with high cyclomatic complexity
func (um *UserManager) ProcessUserData(users []User) map[int]string {
	result := make(map[int]string)

	for _, user := range users {
		if user.IsActive {
			if strings.Contains(user.Email, "@company.com") {
				if user.ID > 1000 {
					if len(user.Name) > 5 {
						if strings.HasPrefix(user.Name, "Admin") {
							if user.ID%2 == 0 {
								result[user.ID] = "super_admin"
							} else {
								result[user.ID] = "admin"
							}
						} else if strings.HasPrefix(user.Name, "Manager") {
							result[user.ID] = "manager"
						} else {
							result[user.ID] = "employee"
						}
					} else {
						result[user.ID] = "short_name"
					}
				} else {
					result[user.ID] = "low_id"
				}
			} else {
				result[user.ID] = "external"
			}
		} else {
			result[user.ID] = "inactive"
		}
	}

	return result
}

// Performance issue - O(n²) algorithm
func (um *UserManager) FindDuplicates(users []User) []User {
	var duplicates []User

	// BAD: Nested loops creating O(n²) complexity
	for i := 0; i < len(users); i++ {
		for j := i + 1; j < len(users); j++ {
			if users[i].Email == users[j].Email {
				duplicates = append(duplicates, users[i])
				duplicates = append(duplicates, users[j])
			}
		}
	}

	return duplicates
}

// Function with path traversal vulnerability
func ReadUserFile(filename string) (string, error) {
	// BAD: No path validation
	fullPath := fmt.Sprintf("/app/user-data/%s", filename)
	
	content, err := os.ReadFile(fullPath)
	if err != nil {
		return "", err
	}
	
	return string(content), nil
}

// Large function for testing function length detection
func MassiveGoFunction() string {
	line1 := "This is line 1"
	line2 := "This is line 2"
	line3 := "This is line 3"
	line4 := "This is line 4"
	line5 := "This is line 5"
	line6 := "This is line 6"
	line7 := "This is line 7"
	line8 := "This is line 8"
	line9 := "This is line 9"
	line10 := "This is line 10"
	line11 := "This is line 11"
	line12 := "This is line 12"
	line13 := "This is line 13"
	line14 := "This is line 14"
	line15 := "This is line 15"
	line16 := "This is line 16"
	line17 := "This is line 17"
	line18 := "This is line 18"
	line19 := "This is line 19"
	line20 := "This is line 20"
	line21 := "This is line 21"
	line22 := "This is line 22"
	line23 := "This is line 23"
	line24 := "This is line 24"
	line25 := "This is line 25"
	line26 := "This is line 26"
	line27 := "This is line 27"
	line28 := "This is line 28"
	line29 := "This is line 29"
	line30 := "This is line 30"
	line31 := "This is line 31"
	line32 := "This is line 32"
	line33 := "This is line 33"
	line34 := "This is line 34"
	line35 := "This is line 35"
	line36 := "This is line 36"
	line37 := "This is line 37"
	line38 := "This is line 38"
	line39 := "This is line 39"
	line40 := "This is line 40"
	line41 := "This is line 41"
	line42 := "This is line 42"
	line43 := "This is line 43"
	line44 := "This is line 44"
	line45 := "This is line 45"
	line46 := "This is line 46"
	line47 := "This is line 47"
	line48 := "This is line 48"
	line49 := "This is line 49"
	line50 := "This is line 50"
	line51 := "This is line 51"
	line52 := "This is line 52"
	line53 := "This is line 53"
	line54 := "This is line 54"
	line55 := "This is line 55"
	line56 := "This is line 56"
	line57 := "This is line 57"
	line58 := "This is line 58"
	line59 := "This is line 59"
	line60 := "This is line 60"
	line61 := "This is line 61"
	line62 := "This is line 62"
	line63 := "This is line 63"
	line64 := "This is line 64"
	line65 := "This is line 65"
	line66 := "This is line 66"
	line67 := "This is line 67"
	line68 := "This is line 68"
	line69 := "This is line 69"
	line70 := "This is line 70"
	line71 := "This is line 71"
	line72 := "This is line 72"
	line73 := "This is line 73"
	line74 := "This is line 74"
	line75 := "This is line 75"
	line76 := "This is line 76"
	line77 := "This is line 77"
	line78 := "This is line 78"
	line79 := "This is line 79"
	line80 := "This is line 80"
	line81 := "This is line 81"
	line82 := "This is line 82"
	line83 := "This is line 83"
	line84 := "This is line 84"
	line85 := "This is line 85"
	line86 := "This is line 86"
	line87 := "This is line 87"
	line88 := "This is line 88"
	line89 := "This is line 89"
	line90 := "This is line 90"
	line91 := "This is line 91"
	line92 := "This is line 92"
	line93 := "This is line 93"
	line94 := "This is line 94"
	line95 := "This is line 95"
	line96 := "This is line 96"
	line97 := "This is line 97"
	line98 := "This is line 98"
	line99 := "This is line 99"
	line100 := "This is line 100"
	line101 := "This is line 101"
	line102 := "This is line 102"
	line103 := "This is line 103"
	line104 := "This is line 104"
	line105 := "This is line 105"

	return fmt.Sprintf("Processed %s through %s", line1, line105)
}

// Function with error swallowing
func (um *UserManager) ProcessUsers(users []User) []User {
	var processed []User

	for _, user := range users {
		result, err := um.validateUser(user)
		if err != nil {
			// BAD: Silent error handling
			continue
		}
		processed = append(processed, result)
	}

	return processed
}

// Helper functions
func (um *UserManager) executeQuery(query string) (*User, error) {
	// Simulate database query
	return &User{}, nil
}

func (um *UserManager) validateUser(user User) (User, error) {
	// Simulate user validation
	return user, nil
}

func main() {
	config := Config{
		Timeout: 30,
		Retries: 3,
		Host:    "localhost",
	}

	um := &UserManager{
		users:  make(map[int]User),
		config: config,
		cache:  make(map[string]interface{}),
	}

	// Test the massive function
	result := MassiveGoFunction()
	fmt.Println(result)

	// Test other functions
	users := []User{
		{ID: 1, Name: "John", Email: "john@company.com", IsActive: true},
		{ID: 2, Name: "Jane", Email: "jane@external.com", IsActive: false},
	}

	processed := um.ProcessUserData(users)
	fmt.Printf("Processed users: %v\n", processed)
}