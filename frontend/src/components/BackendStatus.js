import React, { useState, useEffect } from 'react';
import { toast } from 'react-hot-toast';

const BackendStatus = ({ backendConnected }) => {
  const [backendRunning, setBackendRunning] = useState(backendConnected);
  const [stoppingBackend, setStoppingBackend] = useState(false);
  const [checkingStatus, setCheckingStatus] = useState(false);

  // Update local state when prop changes
  useEffect(() => {
    setBackendRunning(backendConnected);
  }, [backendConnected]);

  useEffect(() => {
    // Add a small delay to avoid race conditions with initial connection
    const timer = setTimeout(() => {
      checkBackendStatus();
    }, 1000);
    
    // Check status every 5 seconds
    const interval = setInterval(checkBackendStatus, 5000);
    
    return () => {
      clearTimeout(timer);
      clearInterval(interval);
    };
  }, []);

  const checkBackendStatus = async () => {
    try {
      setCheckingStatus(true);
      const result = await window.electronAPI.isBackendRunning();
      setBackendRunning(result.running);
    } catch (error) {
      console.error('Failed to check backend status:', error);
      setBackendRunning(false);
    } finally {
      setCheckingStatus(false);
    }
  };

  const stopBackend = async () => {
    try {
      setStoppingBackend(true);
      const result = await window.electronAPI.stopBackend();
      if (result.success) {
        toast.success('Backend stopped successfully');
        setBackendRunning(false);
      } else {
        toast.error('Failed to stop backend');
      }
    } catch (error) {
      console.error('Failed to stop backend:', error);
      toast.error('Failed to stop backend');
    } finally {
      setStoppingBackend(false);
    }
  };

  return (
    <div className="p-6">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Backend Status</h2>
        <p className="text-gray-600">Monitor and manage the automation backend server</p>
      </div>

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center">
            <div className={`w-3 h-3 rounded-full mr-3 ${backendRunning ? 'bg-green-500' : 'bg-red-500'}`}></div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900">
                Backend Status: {backendRunning ? 'Running' : 'Stopped'}
              </h3>
              <p className="text-sm text-gray-500">
                {backendRunning 
                  ? 'The automation backend server is running and responding to requests'
                  : 'The backend server is not running. Close and reopen the app to start it.'
                }
              </p>
            </div>
          </div>
          
          <div className="flex space-x-3">
            <button
              onClick={checkBackendStatus}
              disabled={checkingStatus}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
            >
              {checkingStatus ? 'Checking...' : 'Refresh Status'}
            </button>
            
            {backendRunning && (
              <button
                onClick={stopBackend}
                disabled={stoppingBackend}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 border border-transparent rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 disabled:opacity-50"
              >
                {stoppingBackend ? 'Stopping...' : 'Stop Backend'}
              </button>
            )}
          </div>
        </div>

        {backendRunning && (
          <div className="bg-green-50 border border-green-200 rounded-md p-4">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-green-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-green-800">
                  Backend is healthy and responding
                </h3>
                <div className="mt-2 text-sm text-green-700">
                  <p>All services are running normally and ready to process automation requests.</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {!backendRunning && (
          <div className="bg-red-50 border border-red-200 rounded-md p-4">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-red-800">
                  Backend is not running
                </h3>
                <div className="mt-2 text-sm text-red-700">
                  <p>Please close and reopen the application to start the backend server.</p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default BackendStatus;
