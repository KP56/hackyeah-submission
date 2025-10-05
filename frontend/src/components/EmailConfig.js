import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useSpring, animated } from '@react-spring/web';
import toast from 'react-hot-toast';
import { 
  PlusIcon, 
  TrashIcon, 
  EnvelopeIcon,
  KeyIcon,
  CheckCircleIcon 
} from '@heroicons/react/24/outline';

const EmailConfig = () => {
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [addMethod, setAddMethod] = useState('oauth'); // 'email' or 'oauth'
  const [emailForm, setEmailForm] = useState({ email: '', password: '' });
  const [oauthCode, setOauthCode] = useState('');

  // Spring animation for account count
  const accountCountSpring = useSpring({
    number: accounts.length,
    from: { number: 0 },
    config: { tension: 300, friction: 30 }
  });

  useEffect(() => {
    loadAccounts();
  }, []);

  const loadAccounts = async () => {
    try {
      console.log('EmailConfig: Loading accounts...');
      console.log('EmailConfig: electronAPI available?', !!window.electronAPI);
      const data = await window.electronAPI.getAccounts();
      console.log('EmailConfig: Received data:', data);
      setAccounts(data.accounts || []);
    } catch (error) {
      console.error('Failed to load accounts:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAddEmail = async () => {
    if (!emailForm.email || !emailForm.password) {
      toast.error('Please fill in all fields');
      return;
    }

    try {
      await window.electronAPI.addEmailAccount(emailForm);
      toast.success('Email account added successfully!');
      setEmailForm({ email: '', password: '' });
      setShowAddModal(false);
      loadAccounts();
    } catch (error) {
      toast.error(error.detail || 'Failed to add email account');
    }
  };

  const handleOAuth = async () => {
    try {
      const data = await window.electronAPI.addOAuthAccount();
      console.log('OAuth response:', data);
      
      if (!data || !data.auth_url) {
        toast.error('No OAuth URL received from server');
        return;
      }
      
      // Open OAuth URL in default browser
      await window.electronAPI.openExternal(data.auth_url);
      toast.success('OAuth URL opened in browser. Paste the code below after authorization.');
    } catch (error) {
      console.error('OAuth error:', error);
      if (error.detail) {
        toast.error(`OAuth failed: ${error.detail}`);
      } else {
        toast.error('Failed to initiate OAuth. Please check your Nylas configuration in Settings.');
      }
    }
  };

  const handleOAuthExchange = async () => {
    if (!oauthCode) {
      toast.error('Please enter the OAuth code');
      return;
    }

    try {
      await window.electronAPI.exchangeOAuthCode(oauthCode);
      toast.success('OAuth account added successfully!');
      setOauthCode('');
      setShowAddModal(false);
      loadAccounts();
    } catch (error) {
      toast.error(error.detail || 'Failed to exchange OAuth code');
    }
  };

  const handleRemoveAccount = async (accountId) => {
    try {
      await window.electronAPI.removeAccount(accountId);
      toast.success('Account removed successfully!');
      loadAccounts();
    } catch (error) {
      toast.error('Failed to remove account');
    }
  };

  const getAccountIcon = (accountId) => {
    if (accountId.includes('nylas:')) return '🔗';
    if (accountId.includes('imap:')) return '📧';
    if (accountId.includes('pop3:')) return '📬';
    return '📋';
  };

  const getAccountType = (accountId) => {
    if (accountId.includes('nylas:')) return 'OAuth';
    if (accountId.includes('imap:')) return 'IMAP';
    if (accountId.includes('pop3:')) return 'POP3';
    return 'Unknown';
  };

  return (
    <div className="p-8">
      <div className="max-w-4xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Email Configuration</h1>
          <p className="text-gray-600">Manage your email accounts for automation</p>
        </div>

        {/* Add Account Button */}
        <div className="mb-6">
          <motion.button
            onClick={() => setShowAddModal(true)}
            className="inline-flex items-center px-6 py-3 bg-primary-600 text-white font-medium rounded-lg hover:bg-primary-700 focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 transition-all duration-200 shadow-lg"
            whileHover={{ 
              scale: 1.05,
              boxShadow: "0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)"
            }}
            whileTap={{ scale: 0.95 }}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
          >
            <PlusIcon className="w-5 h-5 mr-2" />
            Add Email Account
          </motion.button>
        </div>

        {/* Accounts List */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-white rounded-xl shadow-sm border border-gray-200"
        >
          <AnimatePresence mode="wait">
            {loading ? (
              <motion.div 
                key="loading"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="flex items-center justify-center py-12"
              >
                <motion.div 
                  className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                />
              </motion.div>
            ) : accounts.length === 0 ? (
              <motion.div 
                key="empty"
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
                className="text-center py-12"
              >
                <motion.div
                  animate={{ 
                    scale: [1, 1.1, 1],
                    rotate: [0, 5, -5, 0]
                  }}
                  transition={{ 
                    duration: 2, 
                    repeat: Infinity, 
                    repeatDelay: 2 
                  }}
                >
                  <EnvelopeIcon className="w-12 h-12 mx-auto text-gray-300 mb-4" />
                </motion.div>
                <h3 className="text-lg font-medium text-gray-900 mb-2">No email accounts</h3>
                <p className="text-gray-600 mb-4">Add your first email account to get started</p>
                <div className="text-sm text-gray-500">
                  Account count: <animated.span>{accountCountSpring.number.to(n => n.toFixed(0))}</animated.span>
                </div>
              </motion.div>
            ) : (
              <motion.div key="accounts" className="divide-y divide-gray-200">
                {accounts.map((account, index) => (
                  <motion.div
                    key={account}
                    initial={{ opacity: 0, x: -20, scale: 0.95 }}
                    animate={{ opacity: 1, x: 0, scale: 1 }}
                    exit={{ opacity: 0, x: 20, scale: 0.95 }}
                    transition={{ 
                      delay: index * 0.1,
                      type: "spring",
                      stiffness: 300,
                      damping: 20
                    }}
                    whileHover={{ 
                      scale: 1.01,
                      x: 5,
                      backgroundColor: "rgba(249, 250, 251, 0.8)"
                    }}
                    className="p-6 hover:bg-gray-50 transition-all duration-200"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-4">
                        <motion.span 
                          className="text-2xl"
                          animate={{ 
                            scale: [1, 1.2, 1],
                            rotate: [0, 10, -10, 0]
                          }}
                          transition={{ 
                            duration: 0.5,
                            delay: index * 0.1
                          }}
                        >
                          {getAccountIcon(account)}
                        </motion.span>
                        <div>
                          <h3 className="text-lg font-medium text-gray-900">{account}</h3>
                          <p className="text-sm text-gray-600">{getAccountType(account)} Account</p>
                        </div>
                      </div>
                      <motion.button
                        onClick={() => handleRemoveAccount(account)}
                        className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                        whileHover={{ 
                          scale: 1.1,
                          backgroundColor: "rgba(239, 68, 68, 0.1)"
                        }}
                        whileTap={{ scale: 0.9 }}
                      >
                        <TrashIcon className="w-5 h-5" />
                      </motion.button>
                    </div>
                  </motion.div>
                ))}
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>

        {/* Add Account Modal */}
        <AnimatePresence>
          {showAddModal && (
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
              onClick={() => setShowAddModal(false)}
            >
              <motion.div
                initial={{ opacity: 0, scale: 0.8, y: 50 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.8, y: 50 }}
                transition={{ 
                  type: "spring", 
                  stiffness: 300, 
                  damping: 25 
                }}
                onClick={(e) => e.stopPropagation()}
                className="bg-white rounded-xl shadow-2xl p-6 w-full max-w-md mx-4"
              >
              <motion.h2 
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="text-xl font-semibold text-gray-900 mb-4"
              >
                Add Email Account
              </motion.h2>
              
              <div className="space-y-4">
                <motion.div 
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.1 }}
                  className="flex space-x-2"
                >
                  <motion.button
                    onClick={() => setAddMethod('email')}
                    disabled={true}
                    className={`flex-1 py-2 px-4 rounded-lg font-medium transition-all duration-200 ${
                      addMethod === 'email'
                        ? 'bg-primary-600 text-white shadow-lg'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                  >
                    Auto-detect (soon!)
                  </motion.button>
                  <motion.button
                    onClick={() => setAddMethod('oauth')}
                    className={`flex-1 py-2 px-4 rounded-lg font-medium transition-all duration-200 ${
                      addMethod === 'oauth'
                        ? 'bg-primary-600 text-white shadow-lg'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                  >
                    OAuth
                  </motion.button>
                </motion.div>

                {addMethod === 'email' ? (
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Email Address
                      </label>
                      <input
                        type="email"
                        value={emailForm.email}
                        onChange={(e) => setEmailForm({ ...emailForm, email: e.target.value })}
                        placeholder="your@email.com"
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Password
                      </label>
                      <input
                        type="password"
                        value={emailForm.password}
                        onChange={(e) => setEmailForm({ ...emailForm, password: e.target.value })}
                        placeholder="Your email password"
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                      />
                    </div>
                    <p className="text-xs text-gray-500">
                      We'll automatically detect your email server settings
                    </p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div className="p-4 bg-blue-50 rounded-lg">
                      <div className="flex items-center">
                        <KeyIcon className="w-5 h-5 text-blue-600 mr-2" />
                        <span className="text-sm font-medium text-blue-900">OAuth Setup</span>
                      </div>
                      <p className="text-sm text-blue-700 mt-1">
                        Click "Get OAuth URL" to open the authorization page in your browser
                      </p>
                      <div className="mt-2 p-2 bg-yellow-50 border border-yellow-200 rounded">
                        <p className="text-xs text-yellow-800">
                          <strong>Note:</strong> Make sure to configure your Nylas API key and Client ID in Settings first.
                        </p>
                      </div>
                    </div>
                    <button
                      onClick={handleOAuth}
                      className="w-full py-2 px-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                    >
                      Get OAuth URL
                    </button>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Authorization Code
                      </label>
                      <input
                        type="text"
                        value={oauthCode}
                        onChange={(e) => setOauthCode(e.target.value)}
                        placeholder="Paste the code from the redirect URL"
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                      />
                    </div>
                  </div>
                )}
              </div>

              <div className="flex justify-end space-x-3 mt-6">
                <button
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={addMethod === 'email' ? handleAddEmail : handleOAuthExchange}
                  className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors flex items-center"
                >
                  <CheckCircleIcon className="w-4 h-4 mr-2" />
                  Add Account
                </button>
              </div>
            </motion.div>
          </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};

export default EmailConfig;
