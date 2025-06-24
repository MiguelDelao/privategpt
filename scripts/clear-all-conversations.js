// Script to clear all conversations
// Run this in the browser console while on the PrivateGPT UI

(async function clearAllConversations() {
  try {
    const { useChatStore } = await import('/src/stores/chatStore.ts');
    const chatStore = useChatStore.getState();
    
    console.log('Clearing all conversations...');
    await chatStore.clearAllSessions();
    console.log('All conversations cleared successfully!');
  } catch (error) {
    console.error('Failed to clear conversations:', error);
    
    // Alternative method using the store directly if available
    if (window.useChatStore) {
      console.log('Trying alternative method...');
      await window.useChatStore.getState().clearAllSessions();
    }
  }
})();