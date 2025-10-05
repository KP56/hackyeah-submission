import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import toast from 'react-hot-toast';
import {
  SparklesIcon,
  PaperAirplaneIcon,
  CheckIcon,
  XMarkIcon,
  ChatBubbleLeftRightIcon,
  ExclamationTriangleIcon
} from '@heroicons/react/24/outline';
import ExecutionErrorDetails from './ExecutionErrorDetails';

const AutomationChat = () => {
  const [currentSuggestion, setCurrentSuggestion] = useState(null);
  const [chatMessages, setChatMessages] = useState([]);
  const [userInput, setUserInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('');
  const [scriptGenerated, setScriptGenerated] = useState(false);
  const [errorDetails, setErrorDetails] = useState(null);
  const [showErrorDetails, setShowErrorDetails] = useState(false);

  const thinkingMessages = [
    "AI is thinking...",
    "Analyzing your request...",
    "Evaluating solution...",
    "Generating automation script...",
    "Checking file operations...",
    "Optimizing code...",
    "Preparing instructions...",
    "Almost ready...",
    "Finalizing details...",
    "Creating magic..."
  ];

  useEffect(() => {
    // Load the most recent pending suggestion
    loadCurrentSuggestion();

    // Listen for when user accepts from popup
    const handleAccepted = async (event, suggestionId) => {
      console.log('Suggestion accepted from popup:', suggestionId);
      await loadSpecificSuggestion(suggestionId);
    };

    window.electronAPI.onSuggestionAccepted(handleAccepted);
  }, []);

  // Cycle through thinking messages while loading
  useEffect(() => {
    if (!loading) {
      setLoadingMessage('');
      return;
    }

    let messageIndex = 0;
    setLoadingMessage(thinkingMessages[0]);

    const interval = setInterval(() => {
      messageIndex = (messageIndex + 1) % thinkingMessages.length;
      setLoadingMessage(thinkingMessages[messageIndex]);
    }, 2000); // Change message every 2 seconds

    return () => clearInterval(interval);
  }, [loading]);

  const loadCurrentSuggestion = async () => {
    try {
      const data = await window.electronAPI.getPendingSuggestions();
      if (data.suggestions && data.suggestions.length > 0) {
        const suggestion = data.suggestions[0];
        
        // Auto-accept the suggestion if it's pending
        if (suggestion.status === 'pending') {
          console.log('Auto-accepting suggestion:', suggestion.suggestion_id);
          await window.electronAPI.acceptSuggestion(suggestion.suggestion_id);
          suggestion.status = 'accepted';
        }
        
        setCurrentSuggestion(suggestion);
        
        // Add AI's initial message
        setChatMessages([{
          role: 'ai',
          content: `I noticed: ${suggestion.pattern_description}\n\nWhat would you like me to automate for you?`,
          timestamp: Date.now()
        }]);
      }
    } catch (error) {
      console.error('Failed to load suggestion:', error);
    }
  };

  const loadSpecificSuggestion = async (suggestionId) => {
    try {
      // First, accept the suggestion
      await window.electronAPI.acceptSuggestion(suggestionId);
      
      // Then load the updated suggestion
      const data = await window.electronAPI.getAllSuggestions();
      const suggestion = data.suggestions.find(s => s.suggestion_id === suggestionId);
      
      if (suggestion) {
        setCurrentSuggestion(suggestion);
        
        // Add AI's initial message
        setChatMessages([{
          role: 'ai',
          content: `I noticed: ${suggestion.pattern_description}\n\nWhat would you like me to automate for you?`,
          timestamp: Date.now()
        }]);
      }
    } catch (error) {
      console.error('Failed to load specific suggestion:', error);
    }
  };

  const handleSendMessage = async () => {
    if (!userInput.trim() || !currentSuggestion || loading) return;

    const userMessage = userInput.trim();
    setUserInput('');

    // Add user message to chat
    setChatMessages(prev => [...prev, {
      role: 'user',
      content: userMessage,
      timestamp: Date.now()
    }]);

    setLoading(true);

    try {
      if (!scriptGenerated) {
        // First interaction - generate script
        const result = await window.electronAPI.provideExplanation(
          currentSuggestion.suggestion_id,
          userMessage
        );

        // Add AI response with script summary
        setChatMessages(prev => [...prev, {
          role: 'ai',
          content: `Great! Here's what I'll do:\n\n${result.summary}\n\nWould you like me to run this script?`,
          timestamp: Date.now(),
          hasSummary: true
        }]);

        setScriptGenerated(true);
        
        // Update suggestion with generated script
        setCurrentSuggestion(prev => ({
          ...prev,
          generated_script: result.script,
          script_summary: result.summary
        }));

      } else {
        // User wants to refine the script
        const result = await window.electronAPI.refineScript(
          currentSuggestion.suggestion_id,
          userMessage
        );

        // Add AI response with new script summary
        setChatMessages(prev => [...prev, {
          role: 'ai',
          content: `I've updated the script:\n\n${result.summary}\n\nWould you like me to run this?`,
          timestamp: Date.now(),
          hasSummary: true
        }]);

        // Update suggestion with refined script
        setCurrentSuggestion(prev => ({
          ...prev,
          generated_script: result.script,
          script_summary: result.summary
        }));
      }
    } catch (error) {
      const errorMsg = error.message || 'Unknown error';
      toast.error(`Failed: ${errorMsg}`);
      console.error('Error details:', error);
      
      setChatMessages(prev => [...prev, {
        role: 'ai',
        content: `Sorry, I encountered an error: ${errorMsg}\n\nPlease try again or describe what you want differently.`,
        timestamp: Date.now(),
        isError: true
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleExecute = () => {
    if (!currentSuggestion || !scriptGenerated) return;

    console.log('[EXECUTE] Running automation in background...');
    
    // Show "STARTED" message IMMEDIATELY
    setChatMessages(prev => [...prev, {
      role: 'ai',
      content: `🚀 Script started! Running your automation in the background...`,
      timestamp: Date.now(),
      isSuccess: true
    }]);
    
    toast.success(`🚀 Script started! Running in the background...`);
    
    // Start execution and poll for status
    window.electronAPI.confirmAndExecute(currentSuggestion.suggestion_id)
      .then(result => {
        console.log('[EXECUTE] Execution started:', result);
        
        // Start polling for status updates
        const pollStatus = async () => {
          try {
            const statusResult = await window.electronAPI.getExecutionStatus(currentSuggestion.suggestion_id);
            console.log('[EXECUTE] Status check:', statusResult);
            
            if (statusResult.status === 'completed') {
              const timeSavedMsg = statusResult.time_saved_seconds 
                ? `${Math.floor(statusResult.time_saved_seconds / 60)} minutes` 
                : 'Unknown time';
              
              // Show "FINISHED" message when actually done
              setChatMessages(prev => [...prev, {
                role: 'ai',
                content: `✅ Script finished successfully!\n\n⏱️ Time saved: ${timeSavedMsg}`,
                timestamp: Date.now(),
                isSuccess: true
              }]);
              
              toast.success(`✅ Automation completed! Time saved: ${timeSavedMsg}`);
              
              // Reset for next automation after showing result
              setTimeout(() => {
                setCurrentSuggestion(null);
                setChatMessages([]);
                setScriptGenerated(false);
                loadCurrentSuggestion();
              }, 3000);
            } else if (statusResult.status === 'failed') {
              // Show error if it failed
              const errorMsg = statusResult.execution_result?.final_error || 'Script failed';
              setChatMessages(prev => [...prev, {
                role: 'ai',
                content: `❌ Script finished with error:\n${errorMsg}`,
                timestamp: Date.now(),
                isError: true
              }]);
              toast.error(`Script failed: ${errorMsg}`);
              
              // Store error details for detailed view
              if (statusResult.error_details) {
                setErrorDetails(statusResult.error_details);
              }
              
              // Reset for next automation after showing result
              setTimeout(() => {
                setCurrentSuggestion(null);
                setChatMessages([]);
                setScriptGenerated(false);
                loadCurrentSuggestion();
              }, 3000);
            } else if (statusResult.status === 'executing') {
              // Still executing, check again in 2 seconds
              setTimeout(pollStatus, 2000);
            }
          } catch (error) {
            console.error('[EXECUTE] Status polling error:', error);
            // If status check fails, assume error
            setChatMessages(prev => [...prev, {
              role: 'ai',
              content: `❌ Script failed to check status:\n${error.message || 'Unknown error'}`,
              timestamp: Date.now(),
              isError: true
            }]);
            toast.error(`Script failed: ${error.message || 'Unknown error'}`);
          }
        };
        
        // Start polling after a short delay
        setTimeout(pollStatus, 1000);
      })
      .catch(error => {
        console.error('[EXECUTE] Background execution error:', error);
        
        // Show error message
        setChatMessages(prev => [...prev, {
          role: 'ai',
          content: `❌ Script failed:\n${error.message || 'Unknown error'}`,
          timestamp: Date.now(),
          isError: true
        }]);
        toast.error(`Script failed: ${error.message || 'Unknown error'}`);
        
        // Reset after error
        setTimeout(() => {
          setCurrentSuggestion(null);
          setChatMessages([]);
          setScriptGenerated(false);
          loadCurrentSuggestion();
        }, 3000);
      });
  };

  const handleReject = async () => {
    if (!currentSuggestion) return;

    try {
      await window.electronAPI.rejectSuggestion(currentSuggestion.suggestion_id);
      toast.success('Suggestion dismissed');
      
      setCurrentSuggestion(null);
      setChatMessages([]);
      setScriptGenerated(false);
      
      // Load next suggestion if any
      setTimeout(loadCurrentSuggestion, 500);
    } catch (error) {
      toast.error('Failed to reject suggestion');
      console.error(error);
    }
  };

  if (!currentSuggestion) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-50 via-white to-blue-50 p-8">
        <div className="max-w-4xl mx-auto">
          <div className="text-center py-20">
            <SparklesIcon className="w-20 h-20 mx-auto text-purple-500 mb-4" />
            <h2 className="text-2xl font-bold text-gray-900 mb-2">No Active Automations</h2>
            <p className="text-gray-600">
              When I detect a pattern in your actions, I'll start a chat here to help you automate it!
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-white to-blue-50 flex flex-col">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 p-4 shadow-sm">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-blue-500 rounded-full flex items-center justify-center">
              <SparklesIcon className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900">Automation Assistant</h1>
              <p className="text-sm text-gray-500">Let's automate your workflow</p>
            </div>
          </div>
          <button
            onClick={handleReject}
            className="px-4 py-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <XMarkIcon className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Chat Messages */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-4xl mx-auto space-y-4">
          <AnimatePresence>
            {chatMessages.map((message, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-2xl rounded-2xl px-6 py-4 ${
                    message.role === 'user'
                      ? 'bg-gradient-to-br from-purple-500 to-blue-500 text-white'
                      : message.isSuccess
                      ? 'bg-green-50 border-2 border-green-200 text-green-900'
                      : message.isError
                      ? 'bg-red-50 border-2 border-red-200 text-red-900'
                      : 'bg-white border border-gray-200 text-gray-900'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <p className="whitespace-pre-wrap flex-1">{message.content}</p>
                    {message.isError && errorDetails && (
                      <button
                        onClick={() => setShowErrorDetails(true)}
                        className="ml-3 p-2 text-red-600 hover:text-red-800 hover:bg-red-100 rounded-lg transition-colors"
                        title="View detailed error information"
                      >
                        <ExclamationTriangleIcon className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>

          {loading && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex justify-start"
            >
              <div className="bg-white border border-gray-200 rounded-2xl px-6 py-4">
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-1">
                    <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                  <span className="text-gray-600 text-sm italic">{loadingMessage}</span>
                </div>
              </div>
            </motion.div>
          )}
        </div>
      </div>

      {/* Input Area */}
      <div className="bg-white border-t border-gray-200 p-4 shadow-lg">
        <div className="max-w-4xl mx-auto">
          {scriptGenerated && (
            <div className="mb-4 flex gap-3">
              <button
                onClick={handleExecute}
                className="flex-1 bg-gradient-to-r from-green-500 to-green-600 text-white px-6 py-3 rounded-xl font-semibold hover:from-green-600 hover:to-green-700 transition-all flex items-center justify-center gap-2"
              >
                <CheckIcon className="w-5 h-5" />
                Run Automation
              </button>
              <button
                onClick={handleReject}
                className="px-6 py-3 bg-gray-100 text-gray-700 rounded-xl font-semibold hover:bg-gray-200 transition-colors"
              >
                Cancel
              </button>
            </div>
          )}
          
          <div className="flex gap-3">
            <input
              type="text"
              value={userInput}
              onChange={(e) => setUserInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
              placeholder={scriptGenerated ? "Want to change something? Tell me..." : "Describe what you want to automate..."}
              disabled={loading}
              className="flex-1 px-6 py-4 border-2 border-gray-200 rounded-xl focus:outline-none focus:border-purple-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            />
            <button
              onClick={handleSendMessage}
              disabled={!userInput.trim()}
              className="bg-gradient-to-r from-purple-500 to-blue-500 text-white px-8 py-4 rounded-xl font-semibold hover:from-purple-600 hover:to-blue-600 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              <PaperAirplaneIcon className="w-5 h-5" />
              Send
            </button>
          </div>
        </div>
      </div>
      
      {/* Error Details Modal */}
      {showErrorDetails && (
        <ExecutionErrorDetails
          errorDetails={errorDetails}
          onClose={() => setShowErrorDetails(false)}
        />
      )}
    </div>
  );
};

export default AutomationChat;

