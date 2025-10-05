import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  ExclamationTriangleIcon, 
  ChevronDownIcon, 
  ChevronRightIcon,
  ClockIcon,
  CodeBracketIcon,
  WrenchScrewdriverIcon,
  XMarkIcon
} from '@heroicons/react/24/outline';

const ExecutionErrorDetails = ({ errorDetails, onClose }) => {
  const [expandedSections, setExpandedSections] = useState({
    attempts: false,
    libraryInstallation: false,
    finalError: true
  });

  const toggleSection = (section) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  if (!errorDetails) return null;

  const formatTimestamp = (timestamp) => {
    if (!timestamp) return 'Unknown time';
    return new Date(timestamp * 1000).toLocaleString();
  };

  const formatExecutionTime = (time) => {
    if (!time) return 'N/A';
    return `${time.toFixed(2)}s`;
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
    >
      <motion.div
        initial={{ scale: 0.9 }}
        animate={{ scale: 1 }}
        className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden"
      >
        {/* Header */}
        <div className="bg-red-50 border-b border-red-200 px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <ExclamationTriangleIcon className="w-6 h-6 text-red-500" />
              <div>
                <h3 className="text-lg font-semibold text-red-800">Script Execution Failed</h3>
                <p className="text-sm text-red-600">
                  Execution ID: {errorDetails.execution_id || 'N/A'} • 
                  {formatTimestamp(errorDetails.timestamp)}
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="text-red-400 hover:text-red-600 transition-colors"
            >
              <XMarkIcon className="w-6 h-6" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 max-h-[calc(90vh-120px)] overflow-y-auto">
          {/* Final Error */}
          <div className="mb-6">
            <button
              onClick={() => toggleSection('finalError')}
              className="flex items-center space-x-2 w-full text-left p-3 bg-red-50 rounded-lg hover:bg-red-100 transition-colors"
            >
              {expandedSections.finalError ? (
                <ChevronDownIcon className="w-5 h-5 text-red-500" />
              ) : (
                <ChevronRightIcon className="w-5 h-5 text-red-500" />
              )}
              <ExclamationTriangleIcon className="w-5 h-5 text-red-500" />
              <span className="font-medium text-red-800">Final Error</span>
            </button>
            
            <AnimatePresence>
              {expandedSections.finalError && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="mt-2 p-4 bg-red-50 border border-red-200 rounded-lg"
                >
                  <pre className="text-sm text-red-800 whitespace-pre-wrap font-mono">
                    {errorDetails.final_error || 'No error message available'}
                  </pre>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Execution Attempts */}
          {errorDetails.attempts && errorDetails.attempts.length > 0 && (
            <div className="mb-6">
              <button
                onClick={() => toggleSection('attempts')}
                className="flex items-center space-x-2 w-full text-left p-3 bg-yellow-50 rounded-lg hover:bg-yellow-100 transition-colors"
              >
                {expandedSections.attempts ? (
                  <ChevronDownIcon className="w-5 h-5 text-yellow-600" />
                ) : (
                  <ChevronRightIcon className="w-5 h-5 text-yellow-600" />
                )}
                <ClockIcon className="w-5 h-5 text-yellow-600" />
                <span className="font-medium text-yellow-800">
                  Execution Attempts ({errorDetails.attempts.length})
                </span>
              </button>
              
              <AnimatePresence>
                {expandedSections.attempts && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className="mt-2 space-y-3"
                  >
                    {errorDetails.attempts.map((attempt, index) => (
                      <div key={index} className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                        <div className="flex items-center justify-between mb-2">
                          <span className="font-medium text-yellow-800">
                            Attempt {attempt.attempt}
                          </span>
                          <div className="flex items-center space-x-4 text-sm text-yellow-600">
                            <span>Return Code: {attempt.return_code}</span>
                            <span>Time: {formatExecutionTime(attempt.execution_time)}</span>
                          </div>
                        </div>
                        
                        {attempt.error && (
                          <div className="mb-2">
                            <span className="text-sm font-medium text-yellow-700">Error:</span>
                            <pre className="text-xs text-yellow-800 whitespace-pre-wrap font-mono mt-1 p-2 bg-yellow-100 rounded">
                              {attempt.error}
                            </pre>
                          </div>
                        )}
                        
                        {attempt.output && (
                          <div>
                            <span className="text-sm font-medium text-yellow-700">Output:</span>
                            <pre className="text-xs text-yellow-800 whitespace-pre-wrap font-mono mt-1 p-2 bg-yellow-100 rounded">
                              {attempt.output}
                            </pre>
                          </div>
                        )}
                      </div>
                    ))}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          )}

          {/* Library Installation */}
          {errorDetails.library_installation && (
            <div className="mb-6">
              <button
                onClick={() => toggleSection('libraryInstallation')}
                className="flex items-center space-x-2 w-full text-left p-3 bg-blue-50 rounded-lg hover:bg-blue-100 transition-colors"
              >
                {expandedSections.libraryInstallation ? (
                  <ChevronDownIcon className="w-5 h-5 text-blue-600" />
                ) : (
                  <ChevronRightIcon className="w-5 h-5 text-blue-600" />
                )}
                <WrenchScrewdriverIcon className="w-5 h-5 text-blue-600" />
                <span className="font-medium text-blue-800">Library Installation</span>
                <span className={`px-2 py-1 rounded-full text-xs ${
                  errorDetails.library_installation.success 
                    ? 'bg-green-100 text-green-800' 
                    : 'bg-red-100 text-red-800'
                }`}>
                  {errorDetails.library_installation.success ? 'Success' : 'Failed'}
                </span>
              </button>
              
              <AnimatePresence>
                {expandedSections.libraryInstallation && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className="mt-2 p-4 bg-blue-50 border border-blue-200 rounded-lg"
                  >
                    {errorDetails.library_installation.installed && 
                     errorDetails.library_installation.installed.length > 0 && (
                      <div className="mb-3">
                        <span className="text-sm font-medium text-blue-700">Successfully Installed:</span>
                        <div className="flex flex-wrap gap-2 mt-1">
                          {errorDetails.library_installation.installed.map((lib, index) => (
                            <span key={index} className="px-2 py-1 bg-green-100 text-green-800 rounded text-xs">
                              {lib}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                    
                    {errorDetails.library_installation.failed && 
                     errorDetails.library_installation.failed.length > 0 && (
                      <div>
                        <span className="text-sm font-medium text-blue-700">Failed to Install:</span>
                        <div className="space-y-2 mt-1">
                          {errorDetails.library_installation.failed.map((failure, index) => (
                            <div key={index} className="p-2 bg-red-100 rounded">
                              <span className="text-sm font-medium text-red-800">{failure.library}</span>
                              {failure.error && (
                                <pre className="text-xs text-red-700 whitespace-pre-wrap font-mono mt-1">
                                  {failure.error}
                                </pre>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="bg-gray-50 border-t border-gray-200 px-6 py-4">
          <div className="flex justify-end space-x-3">
            <button
              onClick={onClose}
              className="px-4 py-2 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300 transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
};

export default ExecutionErrorDetails;
