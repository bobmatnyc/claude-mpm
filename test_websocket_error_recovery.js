/**
 * WebSocket Error Recovery Test
 * 
 * Tests that loading states are properly cleared when WebSocket connections fail
 * or when directory loading requests encounter errors.
 */

(function() {
    'use strict';
    
    console.log('🌐 WebSocket Error Recovery Test Loading...');
    
    const WebSocketErrorTests = {
        async testWebSocketDisconnection() {
            console.log('🔌 Test: WebSocket Disconnection Recovery');
            
            const codeTree = window.codeTree;
            if (!codeTree) {
                console.log('❌ CodeTree instance not found');
                return false;
            }
            
            // Simulate having some loading nodes
            const testPaths = ['src/test1', 'src/test2', 'lib/module1'];
            testPaths.forEach(path => codeTree.loadingNodes.add(path));
            
            console.log(`📊 Added ${testPaths.length} test nodes to loading state`);
            console.log(`📊 Loading nodes before disconnection: ${codeTree.loadingNodes.size}`);
            
            // Simulate WebSocket disconnection by triggering error handler
            codeTree.onAnalysisError({
                message: 'WebSocket connection lost',
                error: 'Connection failed'
            });
            
            console.log(`📊 Loading nodes after error: ${codeTree.loadingNodes.size}`);
            
            const cleared = codeTree.loadingNodes.size === 0;
            console.log(cleared ? '✅ Loading state cleared on WebSocket error' : '❌ Loading state not cleared');
            
            return cleared;
        },
        
        async testDirectoryLoadTimeout() {
            console.log('⏰ Test: Directory Load Timeout Recovery');
            
            const codeTree = window.codeTree;
            if (!codeTree) {
                console.log('❌ CodeTree instance not found');
                return false;
            }
            
            // Add loading nodes
            codeTree.loadingNodes.add('timeout-test-dir');
            
            console.log('📊 Loading nodes before timeout:', codeTree.loadingNodes.size);
            
            // Simulate analysis cancellation (timeout scenario)
            codeTree.onAnalysisCancelled({
                message: 'Request timed out'
            });
            
            console.log('📊 Loading nodes after timeout:', codeTree.loadingNodes.size);
            
            const cleared = codeTree.loadingNodes.size === 0;
            console.log(cleared ? '✅ Loading state cleared on timeout' : '❌ Loading state not cleared');
            
            return cleared;
        },
        
        async testWorkingDirectoryChange() {
            console.log('📁 Test: Working Directory Change Cleanup');
            
            const codeTree = window.codeTree;
            if (!codeTree) {
                console.log('❌ CodeTree instance not found');
                return false;
            }
            
            // Add some loading nodes
            const testPaths = ['old-project/src', 'old-project/lib'];
            testPaths.forEach(path => codeTree.loadingNodes.add(path));
            
            console.log(`📊 Added ${testPaths.length} nodes for old project`);
            console.log('📊 Loading nodes before dir change:', codeTree.loadingNodes.size);
            
            // Simulate working directory change
            codeTree.onWorkingDirectoryChanged('/new/project/path');
            
            console.log('📊 Loading nodes after dir change:', codeTree.loadingNodes.size);
            
            const cleared = codeTree.loadingNodes.size === 0;
            console.log(cleared ? '✅ Loading state cleared on directory change' : '❌ Loading state not cleared');
            
            return cleared;
        },
        
        async runAllTests() {
            console.log('\n🚀 Running WebSocket Error Recovery Tests\n');
            
            const tests = [
                this.testWebSocketDisconnection,
                this.testDirectoryLoadTimeout,
                this.testWorkingDirectoryChange
            ];
            
            let passed = 0;
            let total = tests.length;
            
            for (const test of tests) {
                try {
                    const result = await test.call(this);
                    if (result) passed++;
                } catch (error) {
                    console.error('❌ Test failed:', error);
                }
                console.log(''); // Spacing
            }
            
            console.log(`📊 WebSocket Error Recovery Tests: ${passed}/${total} passed`);
            return passed === total;
        }
    };
    
    // Export to window
    window.WebSocketErrorTests = WebSocketErrorTests;
    
    console.log('💡 WebSocket Error Recovery Tests loaded!');
    console.log('💡 Run window.WebSocketErrorTests.runAllTests() to execute');
    
})();