/**
 * Sample JavaScript file to test tree-sitter-javascript analysis
 * This file contains various JavaScript patterns for testing
 */

// Security issue - hardcoded API key
const API_KEY = "sk-1234567890abcdef";

// Large class that should be flagged
class UserManager {
    constructor(config) {
        this.config = config;
        this.users = new Map();
        this.connections = [];
    }

    // Method with SQL injection vulnerability
    async getUserByName(name) {
        // BAD: String concatenation in SQL
        const query = `SELECT * FROM users WHERE name = '${name}'`;
        return await this.executeQuery(query);
    }

    // Method with command injection risk
    executeSystemCommand(userInput) {
        const { exec } = require('child_process');
        // BAD: Unsanitized user input in system command
        exec(`ls -la ${userInput}`, (error, stdout, stderr) => {
            console.log(stdout);
        });
    }

    // Complex method with nested conditions
    processUserData(userData) {
        let result = {};
        
        for (let user of userData) {
            if (user.active) {
                if (user.type === 'premium') {
                    if (user.credits > 100) {
                        if (user.lastLogin) {
                            if (user.verified) {
                                if (user.country === 'US') {
                                    result[user.id] = {
                                        status: 'eligible',
                                        bonus: user.credits * 0.1
                                    };
                                } else {
                                    result[user.id] = {
                                        status: 'regional',
                                        bonus: user.credits * 0.05
                                    };
                                }
                            } else {
                                result[user.id] = {
                                    status: 'unverified',
                                    bonus: 0
                                };
                            }
                        } else {
                            result[user.id] = {
                                status: 'inactive',
                                bonus: 0
                            };
                        }
                    } else {
                        result[user.id] = {
                            status: 'low_credits',
                            bonus: 0
                        };
                    }
                } else {
                    result[user.id] = {
                        status: 'basic',
                        bonus: 0
                    };
                }
            }
        }
        
        return result;
    }

    // Performance issue - string concatenation in loop
    generateReport(data) {
        let report = "";
        for (let i = 0; i < data.length; i++) {
            for (let j = 0; j < 1000; j++) {
                // BAD: String concatenation in nested loop
                report += `Item ${i}, Detail ${j}: ${data[i].name}\n`;
            }
        }
        return report;
    }

    // Unsafe eval usage
    executeUserCode(code) {
        // BAD: Direct eval of user input
        return eval(code);
    }

    // Memory leak - event listener not removed
    setupEventListeners() {
        const button = document.getElementById('user-button');
        button.addEventListener('click', () => {
            this.handleUserClick();
        });
        // Missing removeEventListener
    }
}

// Function with path traversal vulnerability
function readUserFile(filename) {
    const fs = require('fs');
    // BAD: No path validation
    const filePath = `/app/user-data/${filename}`;
    return fs.readFileSync(filePath, 'utf8');
}

// Large function for testing
function massiveJavaScriptFunction() {
    const line1 = "This is line 1";
    const line2 = "This is line 2";
    const line3 = "This is line 3";
    const line4 = "This is line 4";
    const line5 = "This is line 5";
    const line6 = "This is line 6";
    const line7 = "This is line 7";
    const line8 = "This is line 8";
    const line9 = "This is line 9";
    const line10 = "This is line 10";
    const line11 = "This is line 11";
    const line12 = "This is line 12";
    const line13 = "This is line 13";
    const line14 = "This is line 14";
    const line15 = "This is line 15";
    const line16 = "This is line 16";
    const line17 = "This is line 17";
    const line18 = "This is line 18";
    const line19 = "This is line 19";
    const line20 = "This is line 20";
    const line21 = "This is line 21";
    const line22 = "This is line 22";
    const line23 = "This is line 23";
    const line24 = "This is line 24";
    const line25 = "This is line 25";
    const line26 = "This is line 26";
    const line27 = "This is line 27";
    const line28 = "This is line 28";
    const line29 = "This is line 29";
    const line30 = "This is line 30";
    const line31 = "This is line 31";
    const line32 = "This is line 32";
    const line33 = "This is line 33";
    const line34 = "This is line 34";
    const line35 = "This is line 35";
    const line36 = "This is line 36";
    const line37 = "This is line 37";
    const line38 = "This is line 38";
    const line39 = "This is line 39";
    const line40 = "This is line 40";
    const line41 = "This is line 41";
    const line42 = "This is line 42";
    const line43 = "This is line 43";
    const line44 = "This is line 44";
    const line45 = "This is line 45";
    const line46 = "This is line 46";
    const line47 = "This is line 47";
    const line48 = "This is line 48";
    const line49 = "This is line 49";
    const line50 = "This is line 50";
    const line51 = "This is line 51";
    const line52 = "This is line 52";
    const line53 = "This is line 53";
    const line54 = "This is line 54";
    const line55 = "This is line 55";
    const line56 = "This is line 56";
    const line57 = "This is line 57";
    const line58 = "This is line 58";
    const line59 = "This is line 59";
    const line60 = "This is line 60";
    const line61 = "This is line 61";
    const line62 = "This is line 62";
    const line63 = "This is line 63";
    const line64 = "This is line 64";
    const line65 = "This is line 65";
    const line66 = "This is line 66";
    const line67 = "This is line 67";
    const line68 = "This is line 68";
    const line69 = "This is line 69";
    const line70 = "This is line 70";
    const line71 = "This is line 71";
    const line72 = "This is line 72";
    const line73 = "This is line 73";
    const line74 = "This is line 74";
    const line75 = "This is line 75";
    const line76 = "This is line 76";
    const line77 = "This is line 77";
    const line78 = "This is line 78";
    const line79 = "This is line 79";
    const line80 = "This is line 80";
    const line81 = "This is line 81";
    const line82 = "This is line 82";
    const line83 = "This is line 83";
    const line84 = "This is line 84";
    const line85 = "This is line 85";
    const line86 = "This is line 86";
    const line87 = "This is line 87";
    const line88 = "This is line 88";
    const line89 = "This is line 89";
    const line90 = "This is line 90";
    const line91 = "This is line 91";
    const line92 = "This is line 92";
    const line93 = "This is line 93";
    const line94 = "This is line 94";
    const line95 = "This is line 95";
    const line96 = "This is line 96";
    const line97 = "This is line 97";
    const line98 = "This is line 98";
    const line99 = "This is line 99";
    const line100 = "This is line 100";
    const line101 = "This is line 101";
    const line102 = "This is line 102";
    const line103 = "This is line 103";
    const line104 = "This is line 104";
    const line105 = "This is line 105";

    return `Processed ${line1} through ${line105}`;
}

// Async function with synchronous I/O
async function processUserFiles(fileList) {
    const fs = require('fs');
    let results = [];
    
    for (let file of fileList) {
        // BAD: Synchronous I/O in async function
        const content = fs.readFileSync(file, 'utf8');
        results.push(content);
    }
    
    return results;
}

// Export for testing
module.exports = {
    UserManager,
    readUserFile,
    massiveJavaScriptFunction,
    processUserFiles
};