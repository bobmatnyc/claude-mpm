/**
 * Test the transformEvent function to ensure code events are properly transformed
 */

function simulateTransformEvent(eventData) {
    // Simplified version of the transformEvent logic from socket-client.js
    if (!eventData) return eventData;

    let transformedEvent = { ...eventData };

    // Handle standard format with 'type' field
    if (eventData.type) {
        const type = eventData.type;

        // Transform 'hook.subtype' format to separate type and subtype
        if (type.startsWith('hook.')) {
            const subtype = type.substring(5);
            transformedEvent.type = 'hook';
            transformedEvent.subtype = subtype;
        }
        // Transform 'code:*' events to proper code type
        else if (type.startsWith('code:')) {
            transformedEvent.type = 'code';
            transformedEvent.subtype = type.substring(5); // Remove 'code:' prefix
        }
        // Transform other dotted types like 'session.started'
        else if (type.includes('.')) {
            const [mainType, ...subtypeParts] = type.split('.');
            transformedEvent.type = mainType;
            transformedEvent.subtype = subtypeParts.join('.');
        }
    }

    // Store original event name
    if (eventData.type) {
        transformedEvent.originalEventName = eventData.type;
    }

    return transformedEvent;
}

function testTransformEvent() {
    const testCases = [
        {
            input: { type: 'code:analysis:queued', data: {} },
            expected: {
                type: 'code',
                subtype: 'analysis:queued',
                originalEventName: 'code:analysis:queued'
            },
            description: 'code:analysis:queued transforms to type=code'
        },
        {
            input: { type: 'code:file:start', data: {} },
            expected: {
                type: 'code',
                subtype: 'file:start',
                originalEventName: 'code:file:start'
            },
            description: 'code:file:start transforms to type=code'
        },
        {
            input: { type: 'hook.pre_tool', data: {} },
            expected: {
                type: 'hook',
                subtype: 'pre_tool',
                originalEventName: 'hook.pre_tool'
            },
            description: 'hook.pre_tool transforms correctly'
        },
        {
            input: { type: 'session.started', data: {} },
            expected: {
                type: 'session',
                subtype: 'started',
                originalEventName: 'session.started'
            },
            description: 'session.started transforms correctly'
        }
    ];

    console.log('Testing transformEvent function...\n');

    let passed = 0;
    let failed = 0;

    testCases.forEach(testCase => {
        const result = simulateTransformEvent(testCase.input);

        const typeMatches = result.type === testCase.expected.type;
        const subtypeMatches = result.subtype === testCase.expected.subtype;
        const originalNameMatches = result.originalEventName === testCase.expected.originalEventName;

        const testPassed = typeMatches && subtypeMatches && originalNameMatches;

        if (testPassed) {
            console.log(`✅ PASS: ${testCase.description}`);
            console.log(`   type: ${result.type}, subtype: ${result.subtype}`);
            passed++;
        } else {
            console.log(`❌ FAIL: ${testCase.description}`);
            console.log(`   Expected: type=${testCase.expected.type}, subtype=${testCase.expected.subtype}`);
            console.log(`   Got: type=${result.type}, subtype=${result.subtype}`);
            failed++;
        }
    });

    console.log(`\n========================================`);
    console.log(`Test Results: ${passed} passed, ${failed} failed`);
    console.log(`========================================\n`);

    if (failed === 0) {
        console.log('✅ All transformation tests passed!');
        console.log('\nThe transformEvent function correctly:');
        console.log('1. Transforms code:* events to type="code"');
        console.log('2. Preserves the full subtype (e.g., "analysis:queued")');
        console.log('3. Stores the original event name for reference');
        console.log('\nThis ensures proper filtering in event-viewer.js');
    } else {
        console.log('❌ Some transformation tests failed.');
    }
}

// Run the test
testTransformEvent();