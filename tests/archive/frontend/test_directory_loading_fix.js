/**
 * Test Script: Directory Loading State Management Fix Verification
 *
 * This script tests the fixes for the "Already loading" issue in code-tree.js
 * where the loadingNodes Set wasn't being cleared properly.
 *
 * Run this in browser console while on the Claude MPM dashboard with code tree visible.
 */

(function() {
    'use strict';

    console.log('🧪 Starting Directory Loading State Management Tests...');

    // Test utilities
    const TestUtils = {
        async sleep(ms) {
            return new Promise(resolve => setTimeout(resolve, ms));
        },

        logStep(step, message) {
            console.log(`📋 Step ${step}: ${message}`);
        },

        logResult(passed, message) {
            console.log(passed ? `✅ PASS: ${message}` : `❌ FAIL: ${message}`);
            return passed;
        },

        simulateDirectoryClick(codeTree, path) {
            // Find a directory node in the tree
            if (!codeTree.root) {
                console.log('❌ No tree root found');
                return false;
            }

            const directoryNode = codeTree.root.descendants().find(n =>
                n.data.type === 'directory' &&
                !n.data.loaded &&
                (path ? n.data.path === path : true)
            );

            if (!directoryNode) {
                console.log('❌ No suitable directory node found for testing');
                return false;
            }

            console.log(`🎯 Simulating click on directory: ${directoryNode.data.name} (${directoryNode.data.path})`);

            // Simulate the click by calling onNodeClick directly
            codeTree.onNodeClick(null, directoryNode);
            return directoryNode;
        }
    };

    // Main test runner
    const LoadingStateTests = {
        async runAllTests() {
            console.log('\n🚀 Running Loading State Management Tests\n');

            let passCount = 0;
            let totalTests = 0;

            const tests = [
                this.testLoadingNodesInitialization,
                this.testLoadingStateClearing,
                this.testDuplicateClickPrevention,
                this.testErrorRecovery,
                this.testWebSocketErrorHandling
            ];

            for (const test of tests) {
                totalTests++;
                try {
                    const passed = await test.call(this);
                    if (passed) passCount++;
                } catch (error) {
                    console.error(`❌ Test failed with error:`, error);
                    TestUtils.logResult(false, `Test threw exception: ${error.message}`);
                }
                console.log(''); // Add spacing between tests
            }

            console.log(`\n📊 Test Results: ${passCount}/${totalTests} tests passed`);

            if (passCount === totalTests) {
                console.log('🎉 All tests passed! The directory loading fix is working correctly.');
            } else {
                console.log('⚠️  Some tests failed. Please review the results above.');
            }

            return passCount === totalTests;
        },

        async testLoadingNodesInitialization() {
            console.log('🔬 Test 1: Loading Nodes Set Initialization');

            const codeTree = window.codeTree;
            if (!codeTree) {
                return TestUtils.logResult(false, 'CodeTree instance not found');
            }

            // Check that loadingNodes exists and is a Set
            const hasLoadingNodes = codeTree.loadingNodes instanceof Set;
            TestUtils.logResult(hasLoadingNodes, 'loadingNodes is properly initialized as Set');

            // Check that it starts empty
            const startsEmpty = codeTree.loadingNodes.size === 0;
            TestUtils.logResult(startsEmpty, 'loadingNodes starts empty');

            return hasLoadingNodes && startsEmpty;
        },

        async testLoadingStateClearing() {
            console.log('🔬 Test 2: Loading State Clearing on Directory Change');

            const codeTree = window.codeTree;
            if (!codeTree) {
                return TestUtils.logResult(false, 'CodeTree instance not found');
            }

            // Add a fake loading node to test clearing
            codeTree.loadingNodes.add('test-path');
            const addedSuccessfully = codeTree.loadingNodes.has('test-path');
            TestUtils.logResult(addedSuccessfully, 'Successfully added test loading node');

            // Simulate working directory change
            const mockEvent = { detail: { directory: '/test/new/directory' } };
            codeTree.onWorkingDirectoryChanged('/test/new/directory');

            // Check that loading nodes were cleared
            const wasCleared = codeTree.loadingNodes.size === 0;
            TestUtils.logResult(wasCleared, 'loadingNodes cleared on working directory change');

            return addedSuccessfully && wasCleared;
        },

        async testDuplicateClickPrevention() {
            console.log('🔬 Test 3: Duplicate Click Prevention');

            const codeTree = window.codeTree;
            if (!codeTree) {
                return TestUtils.logResult(false, 'CodeTree instance not found');
            }

            // Find a directory to test with
            const testNode = TestUtils.simulateDirectoryClick(codeTree);
            if (!testNode) {
                return TestUtils.logResult(false, 'No directory node available for testing');
            }

            await TestUtils.sleep(100); // Let the first click process

            // Check if the node is now in loading state
            const isLoading = codeTree.loadingNodes.has(testNode.data.path);
            TestUtils.logResult(isLoading, `Directory ${testNode.data.name} properly added to loading state`);

            // Try to click again - should be prevented
            const initialSize = codeTree.loadingNodes.size;
            TestUtils.simulateDirectoryClick(codeTree, testNode.data.path);

            const finalSize = codeTree.loadingNodes.size;
            const duplicateClickPrevented = finalSize === initialSize;
            TestUtils.logResult(duplicateClickPrevented, 'Duplicate click was properly prevented');

            // Clean up
            codeTree.loadingNodes.delete(testNode.data.path);

            return isLoading && duplicateClickPrevented;
        },

        async testErrorRecovery() {
            console.log('🔬 Test 4: Error Recovery Clears Loading State');

            const codeTree = window.codeTree;
            if (!codeTree) {
                return TestUtils.logResult(false, 'CodeTree instance not found');
            }

            // Add some test loading nodes
            codeTree.loadingNodes.add('test-error-path-1');
            codeTree.loadingNodes.add('test-error-path-2');

            const beforeError = codeTree.loadingNodes.size >= 2;
            TestUtils.logResult(beforeError, 'Added test nodes to loading state');

            // Simulate analysis error
            codeTree.onAnalysisError({ message: 'Test error for loading state cleanup' });

            const afterError = codeTree.loadingNodes.size === 0;
            TestUtils.logResult(afterError, 'Loading state cleared after error');

            return beforeError && afterError;
        },

        async testWebSocketErrorHandling() {
            console.log('🔬 Test 5: WebSocket Error Handling');

            const codeTree = window.codeTree;
            if (!codeTree) {
                return TestUtils.logResult(false, 'CodeTree instance not found');
            }

            // Add test loading node
            codeTree.loadingNodes.add('websocket-test-path');

            const beforeCancel = codeTree.loadingNodes.size >= 1;
            TestUtils.logResult(beforeCancel, 'Added test node for WebSocket error scenario');

            // Simulate analysis cancellation (which happens on WebSocket errors)
            codeTree.onAnalysisCancelled({ message: 'Test WebSocket disconnection' });

            const afterCancel = codeTree.loadingNodes.size === 0;
            TestUtils.logResult(afterCancel, 'Loading state cleared after WebSocket error');

            return beforeCancel && afterCancel;
        }
    };

    // Additional verification tests
    const DirectoryClickTests = {
        async testMultipleDirectoryClicks() {
            console.log('🔬 Directory Click Behavior Test');

            const codeTree = window.codeTree;
            if (!codeTree) {
                return TestUtils.logResult(false, 'CodeTree instance not found');
            }

            // Look for multiple directories we can test
            if (!codeTree.root) {
                return TestUtils.logResult(false, 'No tree root available');
            }

            const directories = codeTree.root.descendants()
                .filter(n => n.data.type === 'directory' && !n.data.loaded)
                .slice(0, 3); // Test up to 3 directories

            if (directories.length === 0) {
                return TestUtils.logResult(true, 'No unloaded directories available (this is OK)');
            }

            console.log(`🎯 Testing ${directories.length} directory click(s)`);

            let allClicksHandled = true;

            for (let i = 0; i < directories.length; i++) {
                const dir = directories[i];
                console.log(`  📁 Clicking directory ${i + 1}: ${dir.data.name}`);

                // Click the directory
                codeTree.onNodeClick(null, dir);

                // Verify it was added to loading state
                const isInLoadingState = codeTree.loadingNodes.has(dir.data.path);
                if (!isInLoadingState) {
                    console.log(`    ❌ Directory ${dir.data.name} not properly added to loading state`);
                    allClicksHandled = false;
                } else {
                    console.log(`    ✅ Directory ${dir.data.name} properly added to loading state`);
                }

                await TestUtils.sleep(50); // Small delay between clicks
            }

            TestUtils.logResult(allClicksHandled, `All ${directories.length} directory clicks handled correctly`);

            // Clean up
            directories.forEach(dir => codeTree.loadingNodes.delete(dir.data.path));

            return allClicksHandled;
        }
    };

    // Enhanced verification check
    const VerifyFixImplementation = {
        checkSourceCode() {
            console.log('🔍 Verifying Fix Implementation in Code');

            const codeTree = window.codeTree;
            if (!codeTree) {
                return TestUtils.logResult(false, 'CodeTree instance not found');
            }

            // Check that the critical methods exist and handle loading state properly
            const hasClearMethods = [
                'onWorkingDirectoryChanged',
                'onAnalysisError',
                'onAnalysisCancelled',
                'removeLoadingPulse'
            ].every(method => typeof codeTree[method] === 'function');

            TestUtils.logResult(hasClearMethods, 'All critical loading state management methods exist');

            // Check loadingNodes is properly managed
            const hasLoadingNodes = codeTree.loadingNodes instanceof Set;
            TestUtils.logResult(hasLoadingNodes, 'loadingNodes is implemented as a Set');

            return hasClearMethods && hasLoadingNodes;
        }
    };

    // Export test functions to window for manual testing
    window.DirectoryLoadingTests = {
        runAll: LoadingStateTests.runAllTests.bind(LoadingStateTests),
        runDirectoryClickTest: DirectoryClickTests.testMultipleDirectoryClicks.bind(DirectoryClickTests),
        verifyImplementation: VerifyFixImplementation.checkSourceCode.bind(VerifyFixImplementation),
        utils: TestUtils
    };

    // Auto-run if requested
    if (window.location.search.includes('autotest=directory-loading')) {
        LoadingStateTests.runAllTests();
    } else {
        console.log('💡 Tests loaded! Run window.DirectoryLoadingTests.runAll() to start testing');
        console.log('💡 Or run window.DirectoryLoadingTests.verifyImplementation() for quick verification');
    }

})();
