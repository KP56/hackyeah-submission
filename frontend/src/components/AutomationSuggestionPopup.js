import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import toast from 'react-hot-toast';
import {
  SparklesIcon,
  XMarkIcon,
  CheckIcon,
  ChatBubbleLeftRightIcon,
  PlayIcon,
  PaperAirplaneIcon,
  ExclamationTriangleIcon
} from '@heroicons/react/24/outline';
import ExecutionErrorDetails from './ExecutionErrorDetails';

const AutomationSuggestionPopup = () => {
  const [suggestions, setSuggestions] = useState([]);
  const [currentSuggestion, setCurrentSuggestion] = useState(null);
  const [showChatModal, setShowChatModal] = useState(false);
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [scriptGenerated, setScriptGenerated] = useState(false);
  const [shownSuggestions, setShownSuggestions] = useState(new Set());
  const [errorDetails, setErrorDetails] = useState(null);
  const [showErrorDetails, setShowErrorDetails] = useState(false);

  useEffect(() => {
    // Poll for pending suggestions every 5 seconds
    const interval = setInterval(async () => {
      try {
        const data = await window.electronAPI.getPendingSuggestions();
        if (data.suggestions && data.suggestions.length > 0) {
          setSuggestions(data.suggestions);
          
          // Show desktop popup only for NEW suggestions we haven't shown yet
          for (const suggestion of data.suggestions) {
            if (!shownSuggestions.has(suggestion.suggestion_id)) {
              console.log('Showing new suggestion:', suggestion.suggestion_id);
              await window.electronAPI.showAutomationPopup(suggestion);
              setCurrentSuggestion(suggestion);
              setShownSuggestions(prev => new Set([...prev, suggestion.suggestion_id]));
              break; // Show one at a time
            }
          }
        }
      } catch (error) {
        console.error('Failed to fetch suggestions:', error);
      }
    }, 5000);

    // Listen for desktop popup responses
    const handleAccepted = (event, suggestionId) => {
      handleAccept();
    };

    const handleRejected = (event, suggestionId) => {
      handleReject();
    };

    window.electronAPI.onSuggestionAccepted(handleAccepted);
    window.electronAPI.onSuggestionRejected(handleRejected);

    return () => clearInterval(interval);
  }, [currentSuggestion]);

  const handleAccept = async () => {
    if (!currentSuggestion) return;

    try {
      await window.electronAPI.acceptSuggestion(currentSuggestion.suggestion_id);
      
      // Start chat with initial AI message
      setChatMessages([
        {
          role: 'assistant',
          content: `Hey! I noticed you were working on something interesting. ${currentSuggestion.pattern_description}\n\nWhat would you like me to automate for you? Please describe what you want the automation to do.`,
          timestamp: Date.now()
        }
      ]);
      
      setShowChatModal(true);
      setScriptGenerated(false);
      setGeneratedScript('');
    } catch (error) {
      toast.error('Failed to accept suggestion');
      console.error(error);
    }
  };

  const handleReject = async () => {
    if (!currentSuggestion) return;

    try {
      await window.electronAPI.rejectSuggestion(currentSuggestion.suggestion_id);
      toast.success('Suggestion dismissed');
      
      // Move to next suggestion
      const remainingSuggestions = suggestions.filter(
        s => s.suggestion_id !== currentSuggestion.suggestion_id
      );
      setSuggestions(remainingSuggestions);
      setCurrentSuggestion(remainingSuggestions[0] || null);
    } catch (error) {
      toast.error('Failed to reject suggestion');
      console.error(error);
    }
  };

  const handleChatSubmit = async () => {
    if (!chatInput.trim() || loading) return;

    const userMessage = chatInput;
    setChatInput('');
    
    // Add user message
    setChatMessages(prev => [...prev, { role: 'user', content: userMessage, timestamp: Date.now() }]);

    setLoading(true);
    try {
      if (!scriptGenerated) {
        // First message - generate script
        const result = await window.electronAPI.provideExplanation(
          currentSuggestion.suggestion_id,
          userMessage
        );
        
        setScriptGenerated(true);
        
        // Add AI response with summary
        setChatMessages(prev => [...prev, {
          role: 'assistant',
          content: result.summary || 'Script generated! (No summary available)',
          timestamp: Date.now()
        }]);
        
        toast.success('✅ Script generated!');
      } else {
        // Refinement - update script
        const result = await window.electronAPI.refineScript(
          currentSuggestion.suggestion_id,
          userMessage
        );
        
        // Add AI response with updated summary
        setChatMessages(prev => [...prev, {
          role: 'assistant',
          content: result.summary || 'Script updated! (No summary available)',
          timestamp: Date.now()
        }]);
        
        toast.success('✅ Script updated!');
      }
    } catch (error) {
      toast.error('❌ Failed to process request');
      console.error('[CHAT ERROR]', error);
      setChatMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Sorry, I had trouble with that. Please try again or describe it differently.',
        timestamp: Date.now(),
        isError: true
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleExecuteScript = () => {
    if (!currentSuggestion || !scriptGenerated) return;

    console.log('[POPUP EXECUTE] Running automation in background...');
    
    // Show "STARTED" message IMMEDIATELY
    toast.success(`🚀 Script started! Running in the background...`);
    
    // Add starting message to chat
    setChatMessages(prev => [...prev, {
      role: 'assistant',
      content: '🚀 Starting automation...',
      timestamp: Date.now(),
      isSystem: true
    }]);
    
    // Start execution and poll for status
    window.electronAPI.confirmAndExecute(currentSuggestion.suggestion_id)
      .then(result => {
        console.log('[POPUP EXECUTE] Execution started:', result);
        
        // Start polling for status updates
        const pollStatus = async () => {
          try {
            const statusResult = await window.electronAPI.getExecutionStatus(currentSuggestion.suggestion_id);
            console.log('[POPUP EXECUTE] Status check:', statusResult);
            
            if (statusResult.status === 'completed') {
              const timeSavedMsg = statusResult.time_saved_seconds 
                ? `${Math.floor(statusResult.time_saved_seconds / 60)} minutes` 
                : 'Unknown time';
              
              setChatMessages(prev => [...prev, {
                role: 'assistant',
                content: `✅ Automation completed successfully!\n\n⏱️ Time saved: ${timeSavedMsg}`,
                timestamp: Date.now(),
                isSuccess: true
              }]);
              
              toast.success(`✅ Automation completed! Time saved: ${timeSavedMsg}`);
              
              // Close modal after 3 seconds
              setTimeout(() => {
                setShowChatModal(false);
                setChatMessages([]);
                setScriptGenerated(false);
                setGeneratedScript('');
                
                // Clear this suggestion
                const remainingSuggestions = suggestions.filter(
                  s => s.suggestion_id !== currentSuggestion.suggestion_id
                );
                setSuggestions(remainingSuggestions);
                setCurrentSuggestion(remainingSuggestions[0] || null);
              }, 3000);
            } else if (statusResult.status === 'failed') {
              const errorMsg = statusResult.execution_result?.final_error || 'Script failed';
              
              setChatMessages(prev => [...prev, {
                role: 'assistant',
                content: `❌ Automation failed:\n${errorMsg}`,
                timestamp: Date.now(),
                isError: true
              }]);
              
              toast.error(`Script failed: ${errorMsg}`);
              
              // Store error details for detailed view
              if (statusResult.error_details) {
                setErrorDetails(statusResult.error_details);
              }
            } else if (statusResult.status === 'executing') {
              // Still executing, check again in 2 seconds
              setTimeout(pollStatus, 2000);
            }
          } catch (error) {
            console.error('[POPUP EXECUTE] Status polling error:', error);
            // If status check fails, assume error
            setChatMessages(prev => [...prev, {
              role: 'assistant',
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
        console.error('[POPUP EXECUTE] Background execution error:', error);
        
        setChatMessages(prev => [...prev, {
          role: 'assistant',
          content: `❌ Automation failed:\n${error.message || 'Unknown error'}`,
          timestamp: Date.now(),
          isError: true
        }]);
        
        toast.error(`Script failed: ${error.message || 'Unknown error'}`);
      });
  };

  if (!currentSuggestion) {
    return null;
  }

  return (
    <>
      {/* Main Suggestion Popup */}
      <AnimatePresence>
        {currentSuggestion && !showChatModal && (
          <motion.div
            initial={{ opacity: 0, y: 50, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 50, scale: 0.9 }}
            className="fixed bottom-8 right-8 z-50"
          >
            <div className="bg-white rounded-2xl shadow-2xl border-2 border-primary-500 max-w-lg w-96 overflow-hidden">
              {/* Header */}
              <div className="bg-gradient-to-r from-primary-500 to-primary-600 p-4">
                <div className="flex items-center justify-between text-white">
                  <div className="flex items-center space-x-2">
                    <SparklesIcon className="w-6 h-6 animate-pulse" />
                    <h3 className="font-bold text-lg">Automation Suggestion</h3>
                  </div>
                  <button
                    onClick={handleReject}
                    className="hover:bg-white/20 rounded-full p-1 transition-colors"
                  >
                    <XMarkIcon className="w-5 h-5" />
                  </button>
                </div>
              </div>

              {/* Content */}
              <div className="p-8">
                <p className="text-gray-700 mb-8 text-base leading-relaxed">
                  {currentSuggestion.pattern_description}
                </p>

                <div className="mb-6 p-4 bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-xl">
                  <p className="text-blue-800 font-medium text-sm">
                    I noticed a pattern in your actions. Would you like me to automate this for you?
                  </p>
                </div>

                {/* Action Buttons */}
                <div className="flex space-x-4">
                  <button
                    onClick={handleReject}
                    className="flex-1 px-6 py-4 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200 transition-all duration-200 font-medium text-sm border border-gray-200"
                  >
                    I don't want LLM assist
                  </button>
                  <button
                    onClick={handleAccept}
                    className="flex-1 px-6 py-4 bg-gradient-to-r from-primary-600 to-primary-700 text-white rounded-xl hover:from-primary-700 hover:to-primary-800 transition-all duration-200 font-medium text-sm flex items-center justify-center space-x-2 shadow-lg hover:shadow-xl"
                  >
                    <ChatBubbleLeftRightIcon className="w-5 h-5" />
                    <span>I want LLM assist</span>
                  </button>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Chat Modal */}
      <AnimatePresence>
        {showChatModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
            onClick={() => !loading && setShowChatModal(false)}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Header */}
              <div className="bg-gradient-to-r from-primary-500 to-primary-600 p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-2xl font-bold text-white flex items-center">
                      <ChatBubbleLeftRightIcon className="w-7 h-7 mr-3" />
                      Automation Assistant
                    </h3>
                    <p className="text-primary-100 text-sm mt-2">
                      Tell me what you want to automate
                    </p>
                  </div>
                  <button
                    onClick={() => !loading && setShowChatModal(false)}
                    className="text-white hover:bg-white/20 rounded-full p-2 transition-colors"
                  >
                    <XMarkIcon className="w-6 h-6" />
                  </button>
                </div>
              </div>

              {/* Chat Messages */}
              <div className="flex-1 overflow-y-auto p-6 space-y-4 bg-gray-50">
                {chatMessages.map((msg, index) => (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-[85%] rounded-2xl px-6 py-5 shadow-sm ${
                        msg.role === 'user'
                          ? 'bg-gradient-to-r from-primary-600 to-primary-700 text-white'
                          : msg.isSuccess
                          ? 'bg-green-50 border-2 border-green-200 text-green-900'
                          : msg.isError
                          ? 'bg-red-50 border-2 border-red-200 text-red-900'
                          : msg.isSystem
                          ? 'bg-blue-50 border-2 border-blue-200 text-blue-900'
                          : 'bg-white border-2 border-gray-200 text-gray-900'
                      }`}
                    >
                      {/* Message content */}
                      <div className="flex items-start justify-between">
                        <div className="whitespace-pre-wrap text-base leading-relaxed flex-1">
                          {msg.content}
                        </div>
                        {msg.isError && errorDetails && (
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

                {loading && (
                  <div className="flex justify-start">
                    <div className="bg-white border border-gray-200 rounded-2xl px-6 py-4 shadow-sm">
                      <div className="flex space-x-2">
                        <div className="w-2 h-2 bg-primary-500 rounded-full animate-bounce"></div>
                        <div className="w-2 h-2 bg-primary-500 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                        <div className="w-2 h-2 bg-primary-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Chat Input */}
              <div className="border-t border-gray-200 p-6 bg-white">
                {scriptGenerated && (
                  <div className="mb-4">
                    <button
                      onClick={handleExecuteScript}
                      disabled={loading}
                      className="w-full bg-gradient-to-r from-green-500 to-green-600 text-white px-6 py-4 rounded-xl font-semibold hover:from-green-600 hover:to-green-700 transition-all flex items-center justify-center gap-2 shadow-lg disabled:opacity-50"
                    >
                      <PlayIcon className="w-5 h-5" />
                      Run This Script
                    </button>
                  </div>
                )}
                
                <div className="flex gap-3">
                  <input
                    type="text"
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && !loading && handleChatSubmit()}
                    placeholder={scriptGenerated ? "Want changes? Tell me what to adjust..." : "Describe what you want to automate..."}
                    disabled={loading}
                    className="flex-1 px-6 py-4 border-2 border-gray-200 rounded-xl focus:outline-none focus:border-primary-500 transition-colors disabled:opacity-50 text-base"
                  />
                  <button
                    onClick={handleChatSubmit}
                    disabled={!chatInput.trim() || loading}
                    className="bg-gradient-to-r from-primary-500 to-primary-600 text-white px-8 py-4 rounded-xl font-semibold hover:from-primary-600 hover:to-primary-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 shadow-lg"
                  >
                    <PaperAirplaneIcon className="w-5 h-5" />
                    Send
                  </button>
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Error Details Modal */}
      {showErrorDetails && (
        <ExecutionErrorDetails
          errorDetails={errorDetails}
          onClose={() => setShowErrorDetails(false)}
        />
      )}
    </>
  );
};

export default AutomationSuggestionPopup;

