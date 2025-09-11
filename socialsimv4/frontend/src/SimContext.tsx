import React, { createContext, useContext } from 'react';
import { useLocalStorage } from "@uidotdev/usehooks";
import { apis } from './lib/api';

export interface ChatMessage {
    sender: string;
    role: string;
    type: 'public' | 'private';
    content: string | {
        reasoning: string;
        execution: string;
        emoji: string;
        Emotion: string;
    };
    timestamp: string;
    subject: string;
    // avatar: string;
}

export interface SimContext {
    isRunning: boolean;
    isStarted: boolean;
    templateCode: string | undefined;
    templateId: number | undefined;
    currSimCode: string | undefined;
    allTemplates: apis.DBTemplate[] | undefined;
    currentTemplate: apis.Template | undefined;
    agents: { [agentName: string]: apis.Agent },
    llmProviders: Record<string, apis.LLMConfig> | undefined;
    initialRounds: number | undefined;
    publicMessages: ChatMessage[];  // Add public messages
    privateMessages: { [agentName: string]: ChatMessage[] };  // Add private messages by agent
    logs: string[] | undefined;
    allEnvs: string[]
}

interface SimContextPair {
    data: SimContext;
    setData: (value: SimContext) => void;
}

const SimContext = createContext<SimContextPair | undefined>(undefined);

export const SimContextProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [get, set] = useLocalStorage<SimContext>('simContext', {
        isRunning: false,
        isStarted: false,
        currSimCode: "",
        templateCode: "",
        templateId: undefined,
        agents: {},
        allTemplates: [],
        currentTemplate: undefined,
        llmProviders: undefined,
        initialRounds: 0,
        publicMessages: [],
        privateMessages: {},
        logs: [],
        allEnvs: []
    });

    return (
        <SimContext.Provider value={{ data: get, setData: set }}>
            {children}
        </SimContext.Provider>
    );
};

export const useSimContext = () => {
    const context = useContext(SimContext);
    if (context === undefined) {
        throw new Error('useGlobalState must be used within a GlobalStateProvider');
    }
    return context;
};
