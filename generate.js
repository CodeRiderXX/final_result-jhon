
document.querySelector('.form').addEventListener('submit', async function (e) {
    e.preventDefault();

    // Collect form data
    const name = document.getElementById('name').value.trim();
    const topic = document.getElementById('file-topic').value.trim();
    const gradeLevel = document.getElementById('grade-level').value;
    const service = document.getElementById('service').value;
    const timeline = document.getElementById('timeline').value;
    const requirements = document.getElementById('requirements').value.trim();
    const pythonModule = document.getElementById('python-module').value;
    const fileInput = document.getElementById('file-upload');
    const file = fileInput && fileInput.files && fileInput.files[0];

    // Helper to read file as text
    function readFileAsText(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result);
            reader.onerror = reject;
            reader.readAsText(file);
        });
    }

    let fileContent = '';
    if (file) {
        try {
            fileContent = await readFileAsText(file);
        } catch (err) {
            alert('Could not read attached file.');
            return;
        }
    }

    // Send all data as a structured object
    // For demo: use a static user_id (e.g., 1). Replace with dynamic user ID if available.
    const userId = 1;
    const paperData = {
        title: topic || 'Untitled Paper',
        user_id: userId,
        content: {
            service,
            grade_level: gradeLevel,
            timeline,
            requirements,
            file_content: fileContent,
            requested_by: name
        },
        python_module: pythonModule
    };

    try {
        const response = await fetch('http://127.0.0.1:8000/api/v1/papers', {
            method: 'POST',
            mode: 'cors',
            credentials: 'omit',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(paperData)
        });

        const responseText = await response.text();
        let result;
        try {
            result = JSON.parse(responseText);
        } catch (jsonError) {
            if (responseText.trim().startsWith('<')) {
                alert('Server error: Received HTML instead of JSON.');
            } else {
                alert('Unexpected response: ' + responseText);
            }
            return;
        }

        if (response.ok) {
            // Clear the form
            this.reset();

            // Redirect to the created question page (e.g., question.html?id=paperId)
            const paperId = result.id || (result.result && result.result.id);
            if (paperId) {
                window.location.href = `question.html?id=${paperId}`;
            } else {
                // Fallback: show the result if no ID is available
                const outputDiv = document.getElementById('generated-questions');
                let questionsHtml = '';
                if (result.questions && Array.isArray(result.questions) && result.questions.length > 0) {
                    questionsHtml = `<h4>Questions:</h4><ol>${result.questions.map(q => `<li>${q}</li>`).join('')}</ol>`;
                } else {
                    questionsHtml = '<p><em>No questions were generated for this paper.</em></p>';
                }
                outputDiv.innerHTML = `
                    <h3>📝 Generated Paper</h3>
                    <p><strong>Paper ID:</strong> ${result.id ?? ''}</p>
                    <p><strong>Title:</strong> ${result.title ?? ''}</p>
                    <pre style="white-space: pre-wrap;">${result.content ?? ''}</pre>
                    ${questionsHtml}
                `;
                outputDiv.style.display = 'block';
                outputDiv.scrollIntoView({ behavior: 'smooth' });
            }
        } else {
            alert('Error creating paper: ' + (result.msg || JSON.stringify(result)));
        }
    } catch (error) {
        alert('Network or server error: ' + error.message);
    }
});
   