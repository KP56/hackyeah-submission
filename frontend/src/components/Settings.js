import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import toast from 'react-hot-toast';
import { 
  CheckCircleIcon, 
  InformationCircleIcon,
  PlusIcon,
  XMarkIcon,
  FolderOpenIcon
} from '@heroicons/react/24/outline';

const Settings = ({ config, updateConfig }) => {
  const [formData, setFormData] = useState({
    nylas: {
      api_key: config?.nylas?.api_key || '',
      client_id: config?.nylas?.client_id || '',
      redirect_uri: config?.nylas?.redirect_uri || 'https://blank.page/',
      api_uri: config?.nylas?.api_uri || 'https://api.us.nylas.com'
    },
    gemini: {
      api_key: config?.gemini?.api_key || '',
      model: config?.gemini?.model || 'gemini-2.5-flash-lite'
    },
    watch: {
      dirs: config?.watch?.dirs || ['./'],
      recent_ops_capacity: config?.watch?.recent_ops_capacity || 100,
      pattern_interval_seconds: config?.watch?.pattern_interval_seconds || 10
    },
    logging: {
      enabled: config?.logging?.enabled || false
    }
  });

  const [saving, setSaving] = useState(false);


  const handleInputChange = (section, field, value) => {
    setFormData(prev => ({
      ...prev,
      [section]: {
        ...prev[section],
        [field]: value
      }
    }));
  };

  const handleArrayChange = (section, field, value) => {
    const array = value.split('\n').filter(item => item.trim());
    handleInputChange(section, field, array);
  };

  const handleAddDirectory = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      const result = await window.electronAPI.selectDirectory();
      if (result && result.filePath) {
        const newDirs = [...formData.watch.dirs, result.filePath];
        const updatedFormData = {
          ...formData,
          watch: {
            ...formData.watch,
            dirs: newDirs
          }
        };
        
        // Update local state
        setFormData(updatedFormData);
        
        // Immediately save to backend
        toast.promise(
          updateConfig(updatedFormData),
          {
            loading: 'Adding directory...',
            success: 'Directory added and watchdog reloaded!',
            error: 'Failed to add directory'
          }
        );
      }
    } catch (error) {
      console.error('Failed to select directory:', error);
      toast.error('Failed to select directory');
    }
  };

  const handleRemoveDirectory = async (e, index) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      const newDirs = formData.watch.dirs.filter((_, i) => i !== index);
      const updatedFormData = {
        ...formData,
        watch: {
          ...formData.watch,
          dirs: newDirs
        }
      };
      
      // Update local state
      setFormData(updatedFormData);
      
      // Immediately save to backend
      await toast.promise(
        updateConfig(updatedFormData),
        {
          loading: 'Removing directory...',
          success: 'Directory removed and watchdog reloaded!',
          error: 'Failed to remove directory'
        }
      );
    } catch (error) {
      console.error('Failed to remove directory:', error);
      toast.error('Failed to remove directory');
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const response = await updateConfig(formData);
      toast.success('Settings saved successfully!');
    } catch (error) {
      toast.error('Failed to save settings');
    } finally {
      setSaving(false);
    }
  };



  const sections = [
    {
      id: 'nylas',
      title: 'Nylas Configuration',
      description: 'Configure your Nylas API credentials for email integration',
      icon: '📧',
      fields: [
        { key: 'api_key', label: 'API Key', type: 'password', placeholder: 'Enter your Nylas API key' },
        { key: 'client_id', label: 'Client ID', type: 'text', placeholder: 'Enter your Nylas Client ID' },
        { key: 'redirect_uri', label: 'Redirect URI', type: 'text', placeholder: 'https://blank.page/' },
        { key: 'api_uri', label: 'API URI', type: 'text', placeholder: 'https://api.us.nylas.com' }
      ]
    },
    {
      id: 'gemini',
      title: 'Gemini AI Configuration',
      description: 'Configure your Google Gemini API key and model for AI features',
      icon: '🤖',
      fields: [
        { key: 'api_key', label: 'API Key', type: 'password', placeholder: 'Enter your Gemini API key' },
        { 
          key: 'model', 
          label: 'Model', 
          type: 'select', 
          placeholder: 'Select Gemini model',
          options: [
            { value: 'gemini-2.5-flash-lite', label: 'Gemini 2.5 Flash Lite (Fastest)' },
            { value: 'gemini-2.5-flash', label: 'Gemini 2.5 Flash (Balanced)' },
            { value: 'gemini-2.5-pro', label: 'Gemini 2.5 Pro (Most Capable)' },
            { value: 'gemini-1.5-flash', label: 'Gemini 1.5 Flash (Legacy)' },
            { value: 'gemini-1.5-pro', label: 'Gemini 1.5 Pro (Legacy)' }
          ],
          help: 'Choose the Gemini model based on your needs. Flash models are faster, Pro models are more capable.'
        }
      ]
    },
    {
      id: 'watch',
      title: 'File Watching Configuration',
      description: 'Configure which directories to monitor for file changes',
      icon: '👁️',
      fields: [
        { 
          key: 'dirs', 
          label: 'Watch Directories', 
          type: 'textarea', 
          placeholder: 'One directory per line',
          help: 'Enter one directory path per line. These will be monitored for file changes.'
        },
        { 
          key: 'recent_ops_capacity', 
          label: 'Recent Operations Capacity', 
          type: 'number', 
          placeholder: '100',
          help: 'Maximum number of recent file operations to keep in memory'
        },
        { 
          key: 'pattern_interval_seconds', 
          label: 'Pattern Detection Interval (seconds)', 
          type: 'number', 
          placeholder: '10',
          help: 'How often to check for patterns in file operations'
        }
      ]
    },
    {
      id: 'logging',
      title: 'Logging Configuration',
      description: 'Enable or disable detailed logging',
      icon: '📝',
      fields: [
        { 
          key: 'enabled', 
          label: 'Enable Logging', 
          type: 'checkbox', 
          help: 'Show detailed logs in the terminal'
        }
      ]
    },
  ];

  return (
    <div className="p-8">
      <div className="max-w-4xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Settings</h1>
          <p className="text-gray-600">Configure your automation assistant</p>
        </div>

        <div className="space-y-8">
          {sections.map((section, index) => (
            <motion.div
              key={section.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
              className="bg-white rounded-xl shadow-sm border border-gray-200 p-6"
            >
              <div className="flex items-center mb-4">
                <span className="text-2xl mr-3">{section.icon}</span>
                <div>
                  <h2 className="text-xl font-semibold text-gray-900">{section.title}</h2>
                  <p className="text-gray-600 text-sm">{section.description}</p>
                </div>
              </div>

              {section.id !== 'backend-management' && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {section.fields.map((field) => (
                    <div key={field.key} className={field.type === 'textarea' ? 'md:col-span-2' : ''}>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        {field.label}
                      </label>
                      
                      {field.type === 'textarea' && field.key === 'dirs' ? (
                        <div className="space-y-3">
                          {/* Directory List */}
                          <div className="space-y-2">
                            <AnimatePresence>
                              {formData[section.id][field.key].map((dir, index) => (
                                <motion.div
                                  key={index}
                                  initial={{ opacity: 0, x: -20 }}
                                  animate={{ opacity: 1, x: 0 }}
                                  exit={{ opacity: 0, x: 20 }}
                                  className="flex items-center gap-3 p-3 bg-gradient-to-r from-gray-50 to-gray-100 border border-gray-200 rounded-lg group hover:border-primary-300 transition-all"
                                >
                                  <FolderOpenIcon className="w-5 h-5 text-primary-600 flex-shrink-0" />
                                  <span className="flex-1 text-sm text-gray-700 truncate font-mono">
                                    {dir}
                                  </span>
                                  <button
                                    type="button"
                                    onClick={(e) => handleRemoveDirectory(e, index)}
                                    className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-all opacity-0 group-hover:opacity-100"
                                    title="Remove directory"
                                  >
                                    <XMarkIcon className="w-4 h-4" />
                                  </button>
                                </motion.div>
                              ))}
                            </AnimatePresence>
                          </div>
                          
                          {/* Add Directory Button */}
                          <button
                            type="button"
                            onClick={handleAddDirectory}
                            className="w-full flex items-center justify-center gap-2 px-4 py-3 border-2 border-dashed border-gray-300 rounded-lg text-gray-600 hover:border-primary-500 hover:text-primary-600 hover:bg-primary-50 transition-all group"
                          >
                            <PlusIcon className="w-5 h-5 group-hover:scale-110 transition-transform" />
                            <span className="font-medium">Add Directory</span>
                          </button>
                        </div>
                      ) : field.type === 'textarea' ? (
                        <textarea
                          value={formData[section.id][field.key].join('\n')}
                          onChange={(e) => handleArrayChange(section.id, field.key, e.target.value)}
                          placeholder={field.placeholder}
                          rows={4}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors"
                        />
                      ) : field.type === 'checkbox' ? (
                        <div className="flex items-center">
                          <input
                            type="checkbox"
                            checked={formData[section.id][field.key]}
                            onChange={(e) => handleInputChange(section.id, field.key, e.target.checked)}
                            className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                          />
                          <span className="ml-2 text-sm text-gray-700">Enable</span>
                        </div>
                      ) : field.type === 'select' ? (
                        <select
                          value={formData[section.id][field.key]}
                          onChange={(e) => handleInputChange(section.id, field.key, e.target.value)}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors"
                        >
                          {field.options.map((option) => (
                            <option key={option.value} value={option.value}>
                              {option.label}
                            </option>
                          ))}
                        </select>
                      ) : (
                        <input
                          type={field.type}
                          value={formData[section.id][field.key]}
                          onChange={(e) => handleInputChange(section.id, field.key, e.target.value)}
                          placeholder={field.placeholder}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors"
                        />
                      )}
                      
                      {field.help && (
                        <p className="mt-1 text-xs text-gray-500 flex items-center">
                          <InformationCircleIcon className="w-4 h-4 mr-1" />
                          {field.help}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </motion.div>
          ))}
        </div>

        <div className="mt-8 flex justify-end">
          <motion.button
            onClick={handleSave}
            disabled={saving}
            className="px-6 py-3 bg-primary-600 text-white font-medium rounded-lg hover:bg-primary-700 focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center"
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            {saving ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                Saving...
              </>
            ) : (
              <>
                <CheckCircleIcon className="w-4 h-4 mr-2" />
                Save Settings
              </>
            )}
          </motion.button>
        </div>

      </div>
    </div>
  );
};

export default Settings;
