document.addEventListener('DOMContentLoaded', () => {
    console.log("DOM loaded. Preparing to initialize Zoom SDK v3.13.2.");

    // UI Element References
    const joinButton = document.getElementById('join-btn');
    const statusIndicator = document.getElementById('status-indicator');
    const statusText = document.getElementById('status-text');
    const logContent = document.getElementById('log');
    const pageHeader = document.getElementById('page-header');
    const setupUI = document.getElementById('setup-ui');
    const zoomRoot = document.getElementById('zmmtg-root');

    // Global variable to store participant roles
    let participantRoles = {};

    function log(message, type = 'info') {
        const entry = document.createElement('div');
        entry.className = `log-entry ${type}`;
        const timestamp = new Date().toLocaleTimeString();
        entry.innerHTML = `<span class="timestamp">${timestamp}</span> ${message}`;
        logContent.appendChild(entry);
        logContent.scrollTop = logContent.scrollHeight;
    }

    function restoreSetupUI(reason) {
        log(`<strong>Action failed:</strong> ${reason}. Restoring setup screen.`, 'error');
        pageHeader.classList.remove('hidden-ui');
        setupUI.classList.remove('hidden-ui');
        zoomRoot.style.display = 'none';

        joinButton.disabled = false;
        joinButton.textContent = 'Connect Bot';
        statusText.textContent = 'Failed';
        statusIndicator.classList.remove('active');
    }

    log('Bot client initialized and ready for connection.', 'info');

    if (typeof SharedArrayBuffer === 'undefined') {
        log('<strong>SharedArrayBuffer is not available.</strong> This may cause issues.', 'error');
    } else {
        log('SharedArrayBuffer is available.', 'success');
    }

    try {
        ZoomMtg.preLoadWasm();
        ZoomMtg.prepareWebSDK();
        log('Zoom SDK prepared successfully.', 'success');
    } catch (error) {
        log(`<strong>Error preparing Zoom SDK:</strong> ${error.message}`, 'error');
        return;
    }

    /**
     * Extracts the Meeting ID from a Zoom meeting URL.
     * @param {string} url - The full Zoom meeting link.
     * @returns {string|null} The meeting ID or null if not found.
     */
    function getMeetingIdFromLink(url) {
        if (!url) return null;
        // This regular expression looks for the number that follows "/j/" in the URL.
        const match = url.match(/\/j\/(\d+)/);
        return match ? match[1] : null;
    }

    joinButton.addEventListener('click', async () => {
        const meetingLink = document.getElementById('meeting-link').value;
        const passWord = document.getElementById('meeting-password').value; // Get passcode from its own field
        const userName = document.getElementById('bot-name').value;

        if (!meetingLink || !userName) {
            alert('Please enter the Meeting Link and a Bot Name.');
            return;
        }
        
        const meetingNumber = getMeetingIdFromLink(meetingLink);
        
        if (!meetingNumber) {
            alert('Could not find a valid Meeting ID in the link. Please check the URL.');
            return;
        }

        // --- The rest of the function is the same as before ---

        pageHeader.classList.add('hidden-ui');
        setupUI.classList.add('hidden-ui');
        zoomRoot.style.display = 'block';

        joinButton.disabled = true;
        joinButton.textContent = 'Joining...';
        statusText.textContent = 'Connecting...';
        statusIndicator.classList.add('active');

        log(`Requesting signature for meeting: ${meetingNumber}`, 'info');
        let signatureResponse;
        try {
            const response = await fetch('/api/generate-sdk-signature', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ meetingNumber, role: 0 })
            });
            if (!response.ok) throw new Error(`Signature request failed: ${response.statusText}`);
            signatureResponse = await response.json();
            log('Signature generated successfully', 'success');
        } catch (error) {
            restoreSetupUI(error.message);
            return;
        }

        if (!signatureResponse || !signatureResponse.signature) {
            restoreSetupUI('Signature was not generated.');
            return;
        }

        log('Initializing Zoom SDK...', 'info');
        ZoomMtg.init({
            debug: false,
            leaveUrl: 'https://www.zoom.com',
            patchJsMedia: true,
            leaveOnPageUnload: true,
            success: () => {
                log('SDK Initialized successfully. Attempting to join meeting...', 'info');
                ZoomMtg.join({
                    signature: signatureResponse.signature,
                    sdkKey: signatureResponse.apiKey,
                    meetingNumber: meetingNumber, // Use the parsed meeting number
                    passWord: passWord,           // Use the manually entered password
                    userName: userName,
                    userEmail: 'ragbot.assistant@example.com',
                    success: (success) => {
                        log('<strong>Successfully joined meeting! Bot is now active.</strong>', 'success');
                        statusText.textContent = 'Connected';
                        joinButton.textContent = 'Connected';
                        setupChatListener(meetingNumber, userName);
                    },
                    error: (err) => {
                        restoreSetupUI(`${err.errorMessage || 'Unknown join error'} (Code: ${err.errorCode})`);
                    }
                });
            },
            error: (err) => {
                restoreSetupUI(`Could not initialize SDK: ${JSON.stringify(err)}`);
            }
        });
    });

    function setupChatListener(meetingId, botName) {
        log(`Setting up chat listener...`);

        const PARTICIPANT_WELCOME_MESSAGE = "Hi! I'm a chat bot, here to help with any questions you have about The Fitness Doctor.";
        const HOST_WELCOME_MESSAGE = "Hello Host! I'm your RAG-Bot assistant, ready to help. You can trigger broadcasts by sending me a command like 'send replay link'. I'll handle attendee questions automatically.";

        // --- KEY CHANGE: Increased timeout to 5 seconds ---
        setTimeout(() => {
            ZoomMtg.getAttendeeslist({
                success: function(data) {
                    const attendees = data?.result?.attendeesList;
                    if (!attendees || attendees.length === 0) return;

                    log('Fetched initial attendee list to send greetings.');
                    participantRoles = {};
                    attendees.forEach(participant => {
                        participantRoles[participant.userId] = { isHost: participant.isHost, isCoHost: participant.isCoHost };
                        
                        if (participant.userName === botName) return; 

                        if (participant.isHost || participant.isCoHost) {
                            log(`Sending HOST welcome DM to ${participant.userName}...`);
                            ZoomMtg.sendChat({ message: HOST_WELCOME_MESSAGE, userId: participant.userId });
                        } else {
                            log(`Sending PARTICIPANT welcome DM to ${participant.userName}...`);
                            ZoomMtg.sendChat({ message: PARTICIPANT_WELCOME_MESSAGE, userId: participant.userId });
                        }
                    });
                },
                error: function(error) { log(`Error getting attendees list: ${JSON.stringify(error)}`, 'error'); }
            });
        }, 5000); // Increased from 3000ms to 5000ms
            
        ZoomMtg.inMeetingServiceListener('onReceiveChatMsg', (chatData) => {
            log(`Chat received from ${chatData.sender}: "${chatData?.content?.text}"`);
            if (chatData.sender === botName) { return log('   ↳ Ignoring own message.'); }
            processChatMessage(meetingId, chatData);
        });

        ZoomMtg.inMeetingServiceListener('onUserJoin', (data) => {
            // CORRECTED: The `data` object itself often represents the user in this event
            const newUser = data;
            if (!newUser || !newUser.userId) {
                console.error("Invalid onUserJoin data structure:", data);
                return;
            };
            
            log(`A new user joined: ${newUser.userName}`);
            if (newUser.userName === botName) return;
            
            // Update our roles map with the new user
            participantRoles[newUser.userId] = { isHost: newUser.isHost, isCoHost: newUser.isCoHost };
            
            const newUserIsPrivileged = newUser.isHost || newUser.isCoHost;
            const messageToSend = newUserIsPrivileged ? HOST_WELCOME_MESSAGE : PARTICIPANT_WELCOME_MESSAGE;
            const roleForLog = newUserIsPrivileged ? "HOST" : "PARTICIPANT";

            setTimeout(() => {
                log(`Sending ${roleForLog} welcome DM to new user ${newUser.userName}...`);
                ZoomMtg.sendChat({
                    message: messageToSend,
                    userId: newUser.userId
                });
            }, 2000); 
        });
    }

    async function processChatMessage(meetingId, chatData) {
        log(`🤖 Processing message from ${chatData.sender}...`);
        try {
            const senderRoleInfo = participantRoles[chatData.senderId] || { isHost: false, isCoHost: false };
            const response = await fetch('/api/process-chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    meeting_id: meetingId, 
                    user_id: chatData.senderId,
                    message: chatData?.content?.text, 
                    user_name: chatData.sender,
                    is_host: senderRoleInfo.isHost,
                    is_cohost: senderRoleInfo.isCoHost
                })
            });
            const data = await response.json();
            
            if (data && data.action === 'broadcast') {
                log(`🎬 Executing command: Broadcasting message.`, 'info');
                const { broadcast_message, ack_message } = data;
                ZoomMtg.sendChat({ message: ack_message, userId: chatData.senderId });
                ZoomMtg.getAttendeeslist({
                    success: function(attendeesData) {
                        const attendees = attendeesData?.result?.attendeesList;
                        if (attendees && attendees.length > 0) {
                            attendees.forEach(participant => {
                                if (participant.userName !== document.getElementById('bot-name').value && participant.userId !== chatData.senderId) {
                                    ZoomMtg.sendChat({ message: broadcast_message, userId: participant.userId });
                                }
                            });
                            log(`✅ Broadcast complete.`, 'success');
                        }
                    }
                });
            } else if (data && data.reply) {
                log(`💭 Sending reply to ${chatData.sender}...`);
                ZoomMtg.sendChat({ message: data.reply, userId: chatData.senderId });
                log(`✅ Reply sent: "${data.reply}"`, 'success');
            } else {
                log('   ↳ Backend determined no reply was needed.');
            }
        } catch (error) {
            log(`❌ <strong>Error processing message:</strong> ${error.message}`, 'error');
        }
    }
});