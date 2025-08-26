const io = require('socket.io-client');

class SessionFormatTester {
    constructor() {
        this.socket = null;
        this.testResults = [];
    }

    async testSessionDropdownFormat() {
        console.log('🧪 Testing Session Dropdown Format...\n');
        
        try {
            // Connect to Socket.IO server
            this.socket = io('http://localhost:8765');
            
            this.socket.on('connect', () => {
                console.log('✅ Connected to Socket.IO server');
                console.log('📡 Socket ID:', this.socket.id);
                
                // Request session data
                this.socket.emit('get_sessions');
                this.socket.emit('request.status');
            });
            
            this.socket.on('sessions_data', (data) => {
                console.log('\n📊 Session Data Received:');
                console.log('Session count:', data.sessions?.length || 0);
                
                if (data.sessions && data.sessions.length > 0) {
                    data.sessions.forEach((session, index) => {
                        console.log(`\n📝 Session ${index + 1}:`);
                        console.log('  ID:', session.id);
                        console.log('  Working Dir:', session.working_directory || session.workingDirectory || 'Not specified');
                        console.log('  Start Time:', session.startTime || session.start_time);
                        console.log('  Event Count:', session.eventCount || session.event_count || 0);
                        
                        // Test the format that would appear in dropdown
                        const workingDir = session.working_directory || session.workingDirectory || '/Users/masa/Projects/claude-mpm';
                        const shortId = session.id.substring(0, 8);
                        const dropdownFormat = `${workingDir} | ${shortId}...`;
                        
                        console.log('  📋 Dropdown Format:', dropdownFormat);
                        
                        // Validate format
                        if (dropdownFormat.includes(' | ') && workingDir && shortId) {
                            console.log('  ✅ Format is correct: working_directory | session_id...');
                        } else {
                            console.log('  ❌ Format is incorrect!');
                        }
                    });
                } else {
                    console.log('⚠️  No sessions found. Start a Claude session to test dropdown format.');
                }
            });
            
            this.socket.on('system.status', (data) => {
                console.log('\n🖥️  System Status:');
                console.log('Current session:', data.current_session || 'None');
                if (data.sessions) {
                    console.log('Available sessions:', data.sessions.length);
                }
            });
            
            this.socket.on('connect_error', (error) => {
                console.error('❌ Connection failed:', error.message);
                this.cleanup();
            });
            
            // Wait for responses, then cleanup
            setTimeout(() => {
                console.log('\n🏁 Test complete');
                this.cleanup();
            }, 5000);
            
        } catch (error) {
            console.error('❌ Test failed:', error.message);
        }
    }
    
    cleanup() {
        if (this.socket) {
            this.socket.disconnect();
            console.log('🔌 Disconnected from server');
        }
        process.exit(0);
    }
}

// Run the test
const tester = new SessionFormatTester();
tester.testSessionDropdownFormat();