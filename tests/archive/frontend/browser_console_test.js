// Browser Console Test for Simple Directory Browser
// Copy and paste this into the browser console at http://localhost:8765/code-simple

console.log('🧪 Starting Browser Console Test for Simple Directory Browser');

// Test 1: Check if SimpleCodeView is available
console.log('\n📋 Test 1: Checking SimpleCodeView availability...');
if (window.simpleCodeView) {
    console.log('✅ SimpleCodeView is available in window');
    console.log('   Current path:', window.simpleCodeView.currentPath);
    console.log('   API base:', window.simpleCodeView.apiBase);
} else {
    console.log('❌ SimpleCodeView NOT found in window');
}

// Test 2: Check DOM elements
console.log('\n🎯 Test 2: Checking DOM elements...');
const elements = {
    'code-container': document.getElementById('code-container'),
    'status-bar': document.getElementById('status-bar'),
    'path-input': document.getElementById('path-input'),
    'directory-contents': document.getElementById('directory-contents'),
    'debug-info': document.getElementById('debug-info')
};

for (const [name, element] of Object.entries(elements)) {
    if (element) {
        console.log(`✅ ${name} found`);
    } else {
        console.log(`❌ ${name} NOT found`);
    }
}

// Test 3: Check current status
console.log('\n📊 Test 3: Current status...');
const statusBar = document.getElementById('status-bar');
if (statusBar) {
    console.log('Current status:', statusBar.textContent);
}

const contentsDiv = document.getElementById('directory-contents');
if (contentsDiv) {
    const hasItems = contentsDiv.innerHTML.includes('<li');
    console.log('Directory contents loaded:', hasItems);
    if (hasItems) {
        const items = contentsDiv.querySelectorAll('li');
        console.log('Number of items displayed:', items.length);
    }
}

// Test 4: Test loading a directory manually
console.log('\n🔄 Test 4: Testing manual directory loading...');
if (window.simpleCodeView) {
    console.log('Testing loadDirectory function...');

    // Test with the current path
    const testPath = '/Users/masa/Projects/claude-mpm/src';
    console.log('Loading test path:', testPath);

    try {
        window.simpleCodeView.loadDirectory(testPath);
        console.log('✅ loadDirectory called successfully');

        // Check result after a delay
        setTimeout(() => {
            const pathInput = document.getElementById('path-input');
            const contentsDiv = document.getElementById('directory-contents');

            console.log('\n📈 Results after 2 seconds:');
            if (pathInput) {
                console.log('Path input value:', pathInput.value);
            }
            if (contentsDiv) {
                const hasContent = contentsDiv.innerHTML.length > 100;
                console.log('Contents loaded:', hasContent);
                if (hasContent && contentsDiv.innerHTML.includes('claude_mpm')) {
                    console.log('✅ Directory contents appear correct');
                } else {
                    console.log('❌ Directory contents may be incorrect');
                    console.log('Contents preview:', contentsDiv.innerHTML.substring(0, 200) + '...');
                }
            }
        }, 2000);

    } catch (error) {
        console.log('❌ loadDirectory failed:', error);
    }
} else {
    console.log('❌ Cannot test - SimpleCodeView not available');
}

// Test 5: Test global functions
console.log('\n🌐 Test 5: Testing global functions...');
if (typeof loadDir === 'function') {
    console.log('✅ loadDir global function exists');
} else {
    console.log('❌ loadDir global function missing');
}

if (typeof goUp === 'function') {
    console.log('✅ goUp global function exists');
} else {
    console.log('❌ goUp global function missing');
}

console.log('\n🎉 Browser Console Test Complete!');
console.log('Check the results above. If you see mostly ✅ marks, the browser is working correctly.');
console.log('If you see ❌ marks, there may be initialization issues.');
console.log('\nTo test interactivity:');
console.log('1. Try typing a path in the input field and clicking Load');
console.log('2. Try clicking on folder names (blue links)');
console.log('3. Try clicking the "Go Up" button');
console.log('4. Watch the Status and Debug Info sections for updates');
