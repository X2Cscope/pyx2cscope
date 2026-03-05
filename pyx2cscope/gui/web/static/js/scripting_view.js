// Scripting View JavaScript
// Handles script execution with real-time output streaming

let scriptSocket = null;
let scriptFile = null;
let isScriptRunning = false;
let scriptLogContent = ''; // Buffer for log download

function initScriptingView() {
    // Initialize Socket.IO connection for scripting
    if (typeof io !== 'undefined') {
        scriptSocket = io('/scripting');

        scriptSocket.on('connect', () => {
            console.log('Scripting socket connected');
            logScriptMessage('Connected to scripting server');
        });

        scriptSocket.on('script_output', (data) => {
            appendScriptOutput(data.output);
        });

        scriptSocket.on('script_finished', (data) => {
            onScriptFinished(data.exit_code);
        });

        scriptSocket.on('script_error', (data) => {
            appendScriptOutput('\nError: ' + data.error + '\n');
            onScriptFinished(1);
        });
    }

    // File input handler
    $('#scriptFileInput').on('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            scriptFile = file;
            $('#scriptPath').val(file.name);
            $('#btnExecuteScript').prop('disabled', false);
            logScriptMessage('Selected script: ' + file.name);
        }
    });

    // Browse button
    $('#btnBrowseScript').on('click', function() {
        $('#scriptFileInput').click();
    });

    // Execute button
    $('#btnExecuteScript').on('click', executeScript);

    // Stop button
    $('#btnStopScript').on('click', stopScript);

    // Help button
    $('#btnScriptHelp').on('click', showScriptHelp);

    // Download log button
    $('#btnDownloadLog').on('click', downloadLog);

    // Clear buttons
    $('#btnClearScriptOutput').on('click', function() {
        $('#scriptOutputText').text('');
        scriptLogContent = '';
        updateDownloadButtonState();
    });

    $('#btnClearScriptLog').on('click', function() {
        $('#scriptLogText').text('');
    });
}

function executeScript() {
    if (!scriptFile) {
        alert('Please select a script file first');
        return;
    }

    if (isScriptRunning) {
        logScriptMessage('A script is already running');
        return;
    }

    // Clear script output and log buffer
    $('#scriptOutputText').text('');
    scriptLogContent = '';

    // Update UI state
    isScriptRunning = true;
    $('#btnExecuteScript').prop('disabled', true);
    $('#btnStopScript').prop('disabled', false);
    $('#btnDownloadLog').prop('disabled', true);
    setScriptStatus('Running...', 'primary');

    // Add header to log
    const timestamp = new Date().toISOString();
    scriptLogContent += '=' .repeat(60) + '\n';
    scriptLogContent += 'Script execution started: ' + timestamp + '\n';
    scriptLogContent += 'Script: ' + scriptFile.name + '\n';
    scriptLogContent += '='.repeat(60) + '\n\n';

    logScriptMessage('Script started: ' + scriptFile.name);

    // Read and send script content
    const reader = new FileReader();
    reader.onload = function(e) {
        const scriptContent = e.target.result;

        if (scriptSocket && scriptSocket.connected) {
            scriptSocket.emit('execute_script', {
                filename: scriptFile.name,
                content: scriptContent
            });
        } else {
            appendScriptOutput('Error: Not connected to server\n');
            onScriptFinished(1);
        }
    };
    reader.readAsText(scriptFile);
}

function stopScript() {
    if (!isScriptRunning) return;

    logScriptMessage('Stop requested...');
    setScriptStatus('Stopping...', 'warning');

    if (scriptSocket && scriptSocket.connected) {
        scriptSocket.emit('stop_script');
    }
}

function onScriptFinished(exitCode) {
    isScriptRunning = false;
    $('#btnExecuteScript').prop('disabled', false);
    $('#btnStopScript').prop('disabled', true);

    // Add footer to log
    const timestamp = new Date().toISOString();
    scriptLogContent += '\n' + '='.repeat(60) + '\n';
    scriptLogContent += 'Script finished: ' + timestamp + '\n';
    scriptLogContent += 'Exit code: ' + exitCode + '\n';
    scriptLogContent += '='.repeat(60) + '\n';

    if (exitCode === 0) {
        setScriptStatus('Completed', 'success');
        logScriptMessage('Script finished successfully');
    } else {
        setScriptStatus('Finished (code ' + exitCode + ')', 'warning');
        logScriptMessage('Script finished with exit code ' + exitCode);
    }

    updateDownloadButtonState();
}

function updateDownloadButtonState() {
    $('#btnDownloadLog').prop('disabled', scriptLogContent.length === 0);
}

function downloadLog() {
    if (!scriptLogContent) {
        alert('No log content to download');
        return;
    }

    // Generate filename based on script name
    let logFileName = 'script_log.txt';
    if (scriptFile) {
        const baseName = scriptFile.name.replace('.py', '');
        logFileName = baseName + '_log.txt';
    }

    // Create blob and download
    const blob = new Blob([scriptLogContent], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = logFileName;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    logScriptMessage('Log downloaded: ' + logFileName);
}

function setScriptStatus(text, variant) {
    const statusEl = $('#scriptStatus');
    statusEl.text(text);
    statusEl.removeClass('bg-secondary bg-primary bg-success bg-warning bg-danger');
    statusEl.addClass('bg-' + variant);
}

function appendScriptOutput(text) {
    const outputEl = $('#scriptOutputText');
    outputEl.append(text);
    // Auto-scroll to bottom
    outputEl.scrollTop(outputEl[0].scrollHeight);

    // Also append to log buffer
    scriptLogContent += text;
}

function logScriptMessage(message) {
    const timestamp = new Date().toLocaleTimeString();
    const formatted = '[' + timestamp + '] ' + message + '\n';
    const logEl = $('#scriptLogText');
    logEl.append(formatted);
    // Auto-scroll to bottom
    logEl.scrollTop(logEl[0].scrollHeight);
}

function showScriptHelp() {
    // Load help content
    $.get('/scripting/help', function(data) {
        $('#scriptHelpContent').html(data.html || formatHelpMarkdown(data.markdown));
        const modal = new bootstrap.Modal(document.getElementById('scriptHelpModal'));
        modal.show();
    }).fail(function() {
        $('#scriptHelpContent').html('<p>Could not load help content.</p>');
        const modal = new bootstrap.Modal(document.getElementById('scriptHelpModal'));
        modal.show();
    });
}

function formatHelpMarkdown(markdown) {
    // Simple markdown to HTML conversion
    if (!markdown) return '<p>No help content available.</p>';

    let html = markdown
        // Code blocks
        .replace(/```python\n([\s\S]*?)```/g, '<pre class="bg-dark text-light p-2 rounded"><code>$1</code></pre>')
        .replace(/```\n?([\s\S]*?)```/g, '<pre class="bg-dark text-light p-2 rounded"><code>$1</code></pre>')
        // Inline code
        .replace(/`([^`]+)`/g, '<code class="bg-light px-1 rounded">$1</code>')
        // Headers
        .replace(/^### (.+)$/gm, '<h5>$1</h5>')
        .replace(/^## (.+)$/gm, '<h4>$1</h4>')
        .replace(/^# (.+)$/gm, '<h3>$1</h3>')
        // Bold
        .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
        // Links
        .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>')
        // Horizontal rules
        .replace(/^---$/gm, '<hr>')
        // Blockquotes
        .replace(/^> (.+)$/gm, '<blockquote class="border-start border-3 ps-3 text-muted">$1</blockquote>')
        // Line breaks
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n/g, '<br>');

    return '<p>' + html + '</p>';
}

// Initialize when document is ready
$(document).ready(function() {
    initScriptingView();
});
