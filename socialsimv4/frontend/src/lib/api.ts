import { ChatMessage } from '@/SimContext';
import axios from 'axios';

export const api = axios.create(({
    baseURL: `${process.env.LISTEN_PREFIX}/api`,
}))

// Setup axios interceptor to add authorization token to requests if needed
// The cookie will be automatically sent by the browser, but we keep token support
// for backwards compatibility
api.interceptors.request.use((config) => {
    const token = localStorage.getItem('token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

// Enable cookies to be sent with requests
api.defaults.withCredentials = true;

export interface AuthResponse {
    access_token: string;
    token_type: string;
}

export interface RegisterRequest {
    username: string;
    email: string;
    full_name: string;
    institution: string;
    password: string;
}

export interface User {
    username: string;
    email?: string;
    full_name?: string;
    institution?: string;
    disabled?: boolean;
    is_admin?: boolean;
    is_sso?: boolean;
    registration_time?: string;
}

export interface FeedbackRequest {
    feedback: string;
}

export interface FeedbackAdminItem {
    id: number;
    user_username: string;
    user_email: string;
    feedback_text: string;
    timestamp: string;
}

export interface AdminTemplate {
    id: number;
    name: string;
    description: string;
    template_json: string;
    username: string;
    creation_time: number;
}


const urls = {
    login: '/login',
    logout: '/logout',
    register: '/register',
    currentUser: '/users/me',
    ssoLogin: '/ssologin',
    fetchTemplate: '/fetch_template',
    fetchTemplates: '/fetch_templates',
    deleteTemplate: '/delete_template',
    startSim: '/start',
    runSim: '/run',
    queryStatus: '/status',
    submitFeedback: '/feedback',
    getFeedbacks: '/admin/feedbacks',
    getAllUserTemplates: '/admin/list_templates',
    getAllUsers: '/admin/list_users',
    userProviders: '/providers',
    messageSocket: (simCode: string) => `/api/ws/${simCode}`
};

export namespace apis {
    export interface EventConfig {
        name: string;
        policy: string;
        websearch: string;
        description: string;
    }

    export interface AgentConfig {
        firstName: string;
        lastName: string;
        age: number;
        avatar: string;
        dailyPlan: string;
        innate: string;
        learned: string;
    }

    export interface Meta {
        template_sim_code: string;
        name: string;
        bullets: string[];
        description: string;
        start_date: string;
        curr_time: string;
        sec_per_step: number;
        maze_name: string;
        persona_names: string[];
        sim_mode: string,
        step: number;
    }


    export interface Agent {
        name: string;
        user_profile: string;
        style: string;
        initial_instruction: string;
        role_prompt: string;
        action_space: string[];
        max_repeat?: number;
        properties?: Record<string, any>;
    }

    export interface LLMConfig {
        usage: 'chat' | 'embedding' | 'completion';
        name: string;
        kind: 'chat' | 'embedding' | 'completion';
        model: string;
        dialect: string;
        base_url: string;
        api_key: string;
        temperature: number;
        max_tokens: number;
        top_p: number;
        frequency_penalty: number;
        presence_penalty: number;
        stream: boolean;
    }

    export interface Event {
        name: string;
        policy: string;
        websearch: string;
        description: string;
    }

    export interface Stage {
        task: string,
        output_format: Record<string, string>
    }


    export interface Template {
        simCode: string;
        events: Event[];
        personas: Agent[];
        meta: Meta;
        workflow: Record<string, Stage>;
        template_json: string;
    }

    export interface DBTemplate {
        id: number;
        name: string;
        description: string;
        template_json: string;
        is_public: boolean;
    }

    export const login = async (username: string, password: string): Promise<AuthResponse> => {
        try {
            // Login endpoint expects form data
            const formData = new FormData();
            formData.append('username', username);
            formData.append('password', password);

            const response = await api.post<AuthResponse>(urls.login, formData);
            return response.data;
        } catch (error) {
            console.error("Login error:", error);
            throw error;
        }
    };

    export const logout = async (): Promise<void> => {
        try {
            await api.post(urls.logout);
        } catch (error) {
            console.error("Logout error:", error);
        }
    };

    export const register = async (userData: RegisterRequest): Promise<User> => {
        try {
            const response = await api.post<User>(urls.register, userData);
            return response.data;
        } catch (error) {
            console.error("Registration error:", error);
            throw error;
        }
    };

    export const getCurrentUser = async (): Promise<User> => {
        try {
            const response = await api.get<User>(urls.currentUser);
            return response.data;
        } catch (error) {
            console.error("Error fetching current user:", error);
            throw error;
        }
    };

    export const ssoLogin = async (params: {
        appId: string;
        username: string;
        time: string;
        sign: string;
    }): Promise<AuthResponse> => {
        try {
            const response = await api.post<AuthResponse>(urls.ssoLogin, params);
            return response.data;
        } catch (error) {
            console.error("SSO login error:", error);
            throw error;
        }
    };

    export const fetchTemplate = async (templateId: number): Promise<Template> => {
        try {
            const response = await api.get<{ template: DBTemplate }>(urls.fetchTemplate, { params: { template_id: templateId } });
            const dbTemplate = response.data.template;
            const templateData = JSON.parse(dbTemplate.template_json);

            return {
                simCode: dbTemplate.name,
                meta: templateData.meta || {
                    name: dbTemplate.name,
                    description: dbTemplate.description,
                    bullets: [],
                    start_date: "February 12, 2023",
                    curr_time: "00:00:00",
                    sec_per_step: 60,
                    maze_name: "default",
                    persona_names: [],
                    sim_mode: "standard",
                    step: 0,
                },
                events: templateData.events || [],
                personas: templateData.agents || [],
                workflow: templateData.workflow || {},
                template_json: dbTemplate.template_json,
            };
        } catch (error) {
            console.error("Error fetching template:", error);
            throw error;
        }
    };

    export const fetchTemplates = async (): Promise<{
        public_templates: DBTemplate[],
        user_templates: DBTemplate[]
    }> => {
        try {
            const response = await api.get<{ templates: DBTemplate[] }>(urls.fetchTemplates);
            return {
                public_templates: response.data.templates,
                user_templates: [] // No longer a concept of user-specific templates in the new API
            };
        } catch (error) {
            console.error("Error fetching templates:", error);
            throw error;
        }
    };

    export const deleteTemplate = async (templateId: number): Promise<void> => {
        try {
            await api.delete(urls.deleteTemplate, { params: { template_id: templateId } });
        } catch (error) {
            console.error("Error deleting template:", error);
            throw error;
        }
    };

    export const startSim = async (
        simCode: string,
        template: Template,
        providers: Record<string, LLMConfig>,
        initial_rounds: number,
    ): Promise<any> => {
        console.log(providers)
        try {
            const response = await api.post(urls.startSim, {
                sim_code: simCode,
                template: template,
                providers: Object.values(providers),
                initial_rounds: initial_rounds,
            });
            return response.data;
        } catch (error) {
            console.error("Error starting simulation:", error);
            throw error;
        }
    };

    export const runSim = async (simCode: string, count: number): Promise<any> => {
        try {
            const response = await api.post(urls.runSim, null, { params: { sim_code: simCode, rounds: count } });
            return response.data;
        } catch (error) {
            console.error("Error running simulation:", error);
            throw error;
        }
    };

    export const updateEnv = async (updateData: any, simCode: string): Promise<any> => {
        console.warn("updateEnv is deprecated and does nothing.");
        return Promise.resolve({ status: "success", message: "Mocked response" });
    };

    export const agentsInfo = async (simCode: string): Promise<Agent[]> => {
        console.warn("agentsInfo is deprecated and does nothing.");
        return Promise.resolve([]);
    };

    export const agentDetail = async (simCode: string, agentName: string): Promise<{
        scratch: Agent,
        a_mem: Record<string, string>,
        s_mem: Record<string, string>,
    }> => {
        console.warn("agentDetail is deprecated and does nothing.");
        return Promise.resolve({
            scratch: {
                name: agentName,
                user_profile: "A mock user profile.",
                style: "mocking",
                initial_instruction: "Mock everyone.",
                role_prompt: "You are a mocker.",
                action_space: ["send_message"],
                max_repeat: 3,
            }, a_mem: {}, s_mem: {}
        });
    };


    export const generateProfilesPlan = async (scenario: string, request: string, agent_count: number): Promise<any> => {
        console.warn("generateProfilesPlan is deprecated and does nothing.");
        return Promise.resolve({ plan: "This is a mock plan." });
    }

    export const generateProfiles = async (plan: any): Promise<{ profiles: Agent[] }> => {
        console.warn("generateProfiles is deprecated and does nothing.");
        return Promise.resolve({ profiles: [] });
    }

    export const sendCommand = async (command: string, simCode: string): Promise<any> => {
        console.warn("sendCommand is deprecated and does nothing.");
        return Promise.resolve({ status: "success", message: "Mocked response" });
    };

    export const privateChat = async (
        simCode: string,
        person: string,
        type: 'interview' | 'whisper',
        history: ChatMessage[],
        content: string
    ): Promise<any> => {
        console.warn("privateChat is deprecated and does nothing.");
        return Promise.resolve({ status: "success", message: "Mocked response" });
    }

    export const publishEvent = async (eventData: EventConfig, simCode: string): Promise<any> => {
        console.warn("publishEvent is deprecated and does nothing.");
        return Promise.resolve({ status: "success", message: "Mocked response" });
    };

    export const queryStatus = async (simCode: string): Promise<'running' | 'idle' | 'terminated'> => {
        try {
            const response = await api.get(urls.queryStatus, { params: { sim_code: simCode } });
            return response.data.status;
        } catch (error) {
            console.error("Error querying status:", error);
            return 'terminated';
        }
    }

    export const getSummary = async (simCode: string): Promise<string> => {
        console.warn("getSummary is deprecated and does nothing.");
        return Promise.resolve("This is a mock summary.");
    }

    export const messageSocket = (simCode: string) => {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        const url = `${protocol}//${host}${urls.messageSocket(simCode)}`;
        return new WebSocket(url);
    };

    export const submitFeedback = async (feedbackData: FeedbackRequest): Promise<any> => {
        try {
            const response = await api.post(urls.submitFeedback, { feedback: feedbackData.feedback });
            return response.data;
        } catch (error) {
            console.error("Error submitting feedback:", error);
            throw error;
        }
    };

    export const getFeedbacks = async (): Promise<FeedbackAdminItem[]> => {
        try {
            const response = await api.get<FeedbackAdminItem[]>(urls.getFeedbacks);
            return response.data;
        } catch (error) {
            console.error("Error fetching feedbacks:", error);
            throw error;
        }
    };

    export const getAllUserTemplates = async (): Promise<AdminTemplate[]> => {
        try {
            const response = await api.get<AdminTemplate[]>(urls.getAllUserTemplates);
            return response.data;
        } catch (error) {
            console.error("Error fetching user templates:", error);
            throw error;
        }
    };

    export const getAllUsers = async (): Promise<User[]> => {
        try {
            const response = await api.get<User[]>(urls.getAllUsers);
            return response.data;
        } catch (error) {
            console.error("Error fetching users:", error);
            throw error;
        }
    };

    export const getUserProviders = async (): Promise<LLMConfig[]> => {
        try {
            const response = await api.get<LLMConfig[]>(urls.userProviders);
            return response.data;
        } catch (error) {
            console.error("Error fetching user providers:", error);
            throw error;
        }
    };

    export const updateUserProviders = async (providers: Record<string, LLMConfig>): Promise<any> => {
        try {
            const providerList = Object.values(providers);
            const response = await api.post(urls.userProviders, providerList);
            return response.data;
        } catch (error) {
            console.error("Error updating user providers:", error);
            throw error;
        }
    };
}
