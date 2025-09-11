import React, { useState, useEffect } from 'react';
import { Navbar } from "@/components/Navbar"
import { BottomNav } from "@/components/BottomNav"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from "@/components/ui/alert-dialog";
import { PlusCircle, Trash2, Upload, Loader2 } from 'lucide-react'
import { useSimContext } from '@/SimContext';
import { apis } from '@/lib/api';
import { RandomAvatar } from '@/components/Avatars';
import { AutoResizeTextarea } from '@/components/autoResizeTextArea';
import DescriptionCard from '@/components/DescriptionCard';
import { InfoTooltip } from '@/components/Tooltip';
import * as pdfjsLib from 'pdfjs-dist';
import mammoth from 'mammoth';

pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
    'pdfjs-dist/build/pdf.worker.min.js',
    import.meta.url,
).toString();


import backgroundImage from '@/assets/Untitled.png'

// Common default values for Agent properties to fix TypeScript errors
const agentDefaults = {
    user_profile: '',
    style: '',
    initial_instruction: '',
    role_prompt: '',
    action_space: ['send_message'],
};

export const AgentsPage = () => {
    const ctx = useSimContext();

    const [agents, setAgents] = useState<(apis.Agent & { id: number })[]>([]);
    const [selectedAgentId, setSelectedAgentId] = useState<number | null>(null);
    const [localAgent, setLocalAgent] = useState<(apis.Agent & { id: number }) | null>(null);
    const [errors, setErrors] = useState<{ [agentId: number]: { [field: string]: string } }>({});
    const [nextAgentNumber, setNextAgentNumber] = useState<number>(1);
    const [isGenerateDialogOpen, setIsGenerateDialogOpen] = useState<boolean>(false);
    const [isGenerating, setIsGenerating] = useState<boolean>(false);
    const [descriptionText, setDescriptionText] = useState<string>("");
    const [descriptionFile, setDescriptionFile] = useState<File | null>(null);
    const [fileContent, setFileContent] = useState<string>("");
    const [agentCountToGenerate, setAgentCountToGenerate] = useState<number>(1);
    const [generationPlan, setGenerationPlan] = useState<Record<string, string> | null>(null);

    const validateAgent = (agent: apis.Agent) => {
        const agentErrors: { [field: string]: string } = {};
        if (!agent.name || agent.name.trim() === '') {
            agentErrors['name'] = 'Name is required.';
        }
        return agentErrors;
    };


    useEffect(() => {
        // Validate all agents whenever agents change
        const newErrors: { [agentId: number]: { [field: string]: string } } = {};
        for (const agent of agents) {
            const agentErrors = validateAgent(agent);
            if (Object.keys(agentErrors).length > 0) {
                newErrors[agent.id] = agentErrors;
            }
        }
        setErrors(newErrors);
    }, [agents]);

    useEffect(() => {
        const fetchTemplate = async () => {
            try {
                if (ctx.data.templateCode && !ctx.data.currentTemplate) {
                    const templateId = parseInt(ctx.data.templateCode, 10);
                    if (!isNaN(templateId)) {
                        const templateData = await apis.fetchTemplate(templateId);
                        ctx.setData({
                            ...ctx.data,
                            currentTemplate: templateData,
                        });
                    }
                }
            } catch (err) {
                console.error("Failed to fetch template detail:", err);
            }
        }

        fetchTemplate();
    }, []);

    useEffect(() => {
        if (ctx.data.currentTemplate?.template_json) {
            try {
                const templateJson = JSON.parse(ctx.data.currentTemplate.template_json);
                if (templateJson.agents) {
                    const agentsWithId = templateJson.agents.map((agent: apis.Agent, index: number) => ({
                        ...agent,
                        id: index + 1,
                    }));
                    setAgents(agentsWithId);
                    setNextAgentNumber(agentsWithId.length + 1);
                    if (agentsWithId.length > 0 && !selectedAgentId) {
                        setSelectedAgentId(agentsWithId[0].id);
                    }
                }
            } catch (error) {
                console.error("Failed to parse template_json:", error);
            }
        }
    }, [ctx.data.currentTemplate]);

    useEffect(() => {
        if (selectedAgentId) {
            const agent = agents.find(a => a.id === selectedAgentId);
            setLocalAgent(agent ? { ...agent } : null);
        } else {
            setLocalAgent(null);
        }
    }, [selectedAgentId, agents]);

    const handleAgentSelect = (id: number) => {
        setSelectedAgentId(id);
    };

    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
        if (localAgent) {
            const { name, value } = e.target;
            const updatedAgent = { ...localAgent, [name]: value };
            setLocalAgent(updatedAgent);

            setAgents(prevAgents =>
                prevAgents.map(agent =>
                    agent.id === updatedAgent.id ? updatedAgent : agent
                )
            );

            updateContextPersonas(agents.map(agent =>
                agent.id === updatedAgent.id ? updatedAgent : agent
            ));

            // Validate agent and update errors
            const agentErrors = validateAgent(updatedAgent);
            setErrors(prevErrors => {
                const newErrors = { ...prevErrors };
                if (Object.keys(agentErrors).length > 0) {
                    newErrors[updatedAgent.id] = agentErrors;
                } else {
                    delete newErrors[updatedAgent.id];
                }
                return newErrors;
            });
        }
    };



    const handleAddAgent = () => {
        const newId = nextAgentNumber;
        const newName = `Agent ${newId}`;

        const newAgent: apis.Agent & { id: number } = {
            id: newId,
            name: newName,
            ...agentDefaults,
        };

        const updatedAgents = [...agents, newAgent];
        setAgents(updatedAgents);
        setSelectedAgentId(newId);
        setNextAgentNumber(nextAgentNumber + 1);
        updateContextPersonas(updatedAgents);

        // Validate new agent and update errors
        const agentErrors = validateAgent(newAgent);
        setErrors(prevErrors => {
            if (Object.keys(agentErrors).length > 0) {
                return { ...prevErrors, [newAgent.id]: agentErrors };
            } else {
                return prevErrors;
            }
        });
    };

    const handleRemoveAgent = (agentId: number) => {
        const updatedAgents = agents.filter(agent => agent.id !== agentId);
        setAgents(updatedAgents);
        setSelectedAgentId(updatedAgents.length > 0 ? updatedAgents[0].id : null);
        updateContextPersonas(updatedAgents);

        // Remove errors related to the deleted agent
        setErrors(prevErrors => {
            const { [agentId]: _, ...rest } = prevErrors;
            return rest;
        });
    };

    const updateContextPersonas = (updatedAgents: (apis.Agent & { id: number })[]) => {
        if (ctx.data.currentTemplate) {
            try {
                const templateJson = JSON.parse(ctx.data.currentTemplate.template_json);
                templateJson.agents = updatedAgents.map(({ id, ...agent }) => agent);
                ctx.setData({
                    ...ctx.data,
                    currentTemplate: {
                        ...ctx.data.currentTemplate,
                        template_json: JSON.stringify(templateJson, null, 2),
                    }
                });
            } catch (error) {
                console.error("Failed to update template_json:", error);
            }
        }
    };

    const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files.length > 0) {
            const file = e.target.files[0];
            setDescriptionFile(file);
            setDescriptionText("");
            setFileContent("");

            const extension = file.name.split('.').pop()?.toLowerCase();

            try {
                let text = "";
                if (extension === 'txt') {
                    text = await file.text();
                } else if (extension === 'pdf') {
                    const arrayBuffer = await file.arrayBuffer();
                    const pdf = await pdfjsLib.getDocument(arrayBuffer).promise;
                    const numPages = pdf.numPages;
                    for (let i = 1; i <= numPages; i++) {
                        const page = await pdf.getPage(i);
                        const content = await page.getTextContent();
                        text += content.items.map((item: any) => item.str).join(' ');
                    }
                } else if (extension === 'docx') {
                    const arrayBuffer = await file.arrayBuffer();
                    const result = await mammoth.extractRawText({ arrayBuffer });
                    text = result.value;
                } else if (extension === 'doc') {
                    console.error(".doc format is not supported. Please convert to .docx");
                }
                setFileContent(text);
            } catch (error) {
                console.error("Error parsing file:", error);
            }
        }
    };

    const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        setDescriptionText(e.target.value);
        setDescriptionFile(null);
        setFileContent("");
    };

    const handleGetPlan = async () => {
        const request = descriptionText || fileContent;
        if (!request) {
            return;
        }
        setIsGenerating(true);
        try {
            const scenario = ctx.data.currentTemplate?.meta.name || "a social simulation";
            const plan = await apis.generateProfilesPlan(scenario, request, agentCountToGenerate);
            setGenerationPlan(plan);
        } catch (error) {
            console.error("Error generating plan:", error);
        } finally {
            setIsGenerating(false);
        }
    };

    const handleGenerateAgentsFromPlan = async () => {
        if (!generationPlan) {
            return;
        }
        setIsGenerating(true);
        try {
            const { profiles } = await apis.generateProfiles(generationPlan);
            const newAgents = profiles.map((profile, index) => ({
                ...profile,
                id: nextAgentNumber + index,
            }));
            const updatedAgents = [...agents, ...newAgents];
            setAgents(updatedAgents);
            setNextAgentNumber(nextAgentNumber + newAgents.length);
            updateContextPersonas(updatedAgents);
            setIsGenerateDialogOpen(false);
            setDescriptionText("");
            setDescriptionFile(null);
            setGenerationPlan(null);
        } catch (error) {
            console.error("Error generating agents:", error);
        } finally {
            setIsGenerating(false);
        }
    };

    const isNextDisabled = Object.keys(errors).length > 0 || agents.length === 0;

    return (
        <div className="flex flex-col min-h-screen bg-gray-100" style={{ backgroundImage: `url(${backgroundImage})`, backgroundSize: '100% 100%', backgroundRepeat: 'no-repeat', backgroundAttachment: 'fixed' }}>
            <Navbar className="border-white border-b-[1px] border-opacity-40 bg-white bg-opacity-40 backdrop-filter backdrop-blur-lg dark:border-b-slate-700 dark:bg-background" />
            <div className="container mx-auto">
                <h2 className="text-5xl font-bold my-12 text-left text-black-800"><span className="font-mono">Step 3.</span>自定义智能体</h2>

                <DescriptionCard
                    title="配置仿真智能体"
                    description="您可以自定义社会仿真实验中的各个智能体。您可以添加新的智能体，编辑现有智能体的各项属性，如姓名、年龄、性格特征、日常计划、生活方式和居住区域等。这些设置将决定智能体在仿真中的行为模式、互动方式和决策过程。通过精心配置这些参数，您可以创建更真实、更丰富的仿真环境，从而获得更有价值的实验结果。"
                />


                <Card className="bg-opacity-70 bg-white overflow-hidden">
                    <CardContent className='px-0'>
                        <div className="flex">
                            <div className={`${localAgent ? 'w-1/3' : 'w-full'} border-r border-gray-200`}>
                                <div className="p-4">
                                    <div className="space-y-2">
                                        {agents.map(agent => (
                                            <div
                                                key={agent.id}
                                                className={`flex items-center justify-between p-2 rounded-lg transition-colors duration-200 cursor-pointer ${selectedAgentId === agent.id ? 'bg-secondary' : 'hover:bg-secondary/50'
                                                    }`}
                                                onClick={() => handleAgentSelect(agent.id)}
                                            >
                                                <div className="flex items-center space-x-4 flex-grow">
                                                    <RandomAvatar className="h-10 w-10" name={`${agent.name}`} />
                                                    <span className="font-medium">{`${agent.name}`}</span>
                                                </div>
                                                <AlertDialog>
                                                    <AlertDialogTrigger asChild>
                                                        <Button
                                                            variant="ghost"
                                                            size="sm"
                                                            className="text-gray-400 hover:text-red-600 hover:bg-red-50 transition-all duration-200 ml-2"
                                                            onClick={(e) => e.stopPropagation()}
                                                        >
                                                            <Trash2 className="h-4 w-4" />
                                                        </Button>
                                                    </AlertDialogTrigger>
                                                    <AlertDialogContent>
                                                        <AlertDialogHeader>
                                                            <AlertDialogTitle>您确定要删除这个智能体吗？</AlertDialogTitle>
                                                            <AlertDialogDescription>
                                                                该操作无法撤销。数据将从服务器上永远清除。
                                                            </AlertDialogDescription>
                                                        </AlertDialogHeader>
                                                        <AlertDialogFooter>
                                                            <AlertDialogCancel>取消</AlertDialogCancel>
                                                            <AlertDialogAction
                                                                onClick={(e) => {
                                                                    e.stopPropagation();
                                                                    handleRemoveAgent(agent.id);
                                                                }}
                                                                className="bg-red-600 hover:bg-red-700"
                                                            >
                                                                删除
                                                            </AlertDialogAction>
                                                        </AlertDialogFooter>
                                                    </AlertDialogContent>
                                                </AlertDialog>
                                            </div>
                                        ))}
                                    </div>
                                    <Button onClick={handleAddAgent} className="w-full mt-6 bg-indigo-500 hover:bg-indigo-600 text-white">
                                        <PlusCircle className="mr-2 h-4 w-4" /> 添加新智能体
                                    </Button>
                                    <Button onClick={() => setIsGenerateDialogOpen(true)} className="w-full mt-3 bg-teal-600 hover:bg-teal-700 text-white">
                                        <Upload className="mr-2 h-4 w-4" /> 按照描述生成
                                    </Button>

                                    {/* 按照描述生成对话框 */}
                                    <AlertDialog open={isGenerateDialogOpen} onOpenChange={(isOpen) => {
                                        setIsGenerateDialogOpen(isOpen);
                                        if (!isOpen) {
                                            setGenerationPlan(null);
                                            setDescriptionFile(null);
                                            setDescriptionText("");
                                        }
                                    }}>
                                        <AlertDialogContent className="max-w-2xl">
                                            <AlertDialogHeader>
                                                <AlertDialogTitle>通过描述生成智能体</AlertDialogTitle>
                                                <AlertDialogDescription>
                                                    {generationPlan ? "请编辑生成计划，然后点击“生成智能体”" : "请输入描述文本或上传文件，系统将根据您的描述生成相应的智能体。"}
                                                </AlertDialogDescription>
                                            </AlertDialogHeader>
                                            {generationPlan ? (
                                                <div className="space-y-4 my-4">
                                                    {Object.entries(generationPlan).map(([key, value]) => (
                                                        <div key={key}>
                                                            <label className="block text-sm font-medium text-gray-700 mb-1">{key}</label>
                                                            <AutoResizeTextarea
                                                                value={value}
                                                                onChange={(e) => setGenerationPlan({ ...generationPlan, [key]: e.target.value })}
                                                                className="w-full min-h-[80px] p-2 border rounded-md"
                                                                disabled={isGenerating}
                                                            />
                                                        </div>
                                                    ))}
                                                </div>
                                            ) : (
                                                <div className="space-y-4 my-4">
                                                    <div>
                                                        <label className="block text-sm font-medium text-gray-700 mb-1">生成数量</label>
                                                        <Input
                                                            type="number"
                                                            value={agentCountToGenerate}
                                                            onChange={(e) => setAgentCountToGenerate(parseInt(e.target.value, 10) || 1)}
                                                            className="w-full"
                                                            min="1"
                                                            disabled={isGenerating}
                                                        />
                                                    </div>
                                                    <div>
                                                        <label className="block text-sm font-medium text-gray-700 mb-1">文本描述</label>
                                                        <AutoResizeTextarea
                                                            value={descriptionText}
                                                            onChange={handleTextChange}
                                                            placeholder="请描述您想要生成的智能体..."
                                                            className="w-full min-h-[100px] p-2 border rounded-md"
                                                            disabled={isGenerating}
                                                        />
                                                    </div>
                                                    <div>
                                                        <label className="block text-sm font-medium text-gray-700 mb-1">或者上传文件</label>
                                                        <div className="flex items-center space-x-2">
                                                            <Input
                                                                type="file"
                                                                onChange={handleFileChange}
                                                                className="flex-1"
                                                                disabled={isGenerating}
                                                                accept=".txt,.pdf,.doc,.docx"
                                                            />
                                                        </div>
                                                        {descriptionFile && (
                                                            <p className="text-sm text-gray-600 mt-1">
                                                                已选择文件: {descriptionFile.name}
                                                            </p>
                                                        )}
                                                    </div>
                                                </div>
                                            )}
                                            <AlertDialogFooter>
                                                <AlertDialogCancel disabled={isGenerating}>取消</AlertDialogCancel>
                                                {generationPlan ? (
                                                    <Button
                                                        onClick={handleGenerateAgentsFromPlan}
                                                        disabled={isGenerating || !generationPlan}
                                                        className={`${isGenerating ? 'bg-gray-400' : 'bg-green-600 hover:bg-green-700'} text-white`}
                                                    >
                                                        {isGenerating ? (
                                                            <>
                                                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                                                生成中...
                                                            </>
                                                        ) : (
                                                            "生成智能体"
                                                        )}
                                                    </Button>
                                                ) : (
                                                    <Button
                                                        onClick={handleGetPlan}
                                                        disabled={isGenerating || (!descriptionText && !descriptionFile)}
                                                        className={`${isGenerating ? 'bg-gray-400' : 'bg-blue-600 hover:bg-blue-700'} text-white`}
                                                    >
                                                        {isGenerating ? (
                                                            <>
                                                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                                                生成中...
                                                            </>
                                                        ) : (
                                                            "获取计划"
                                                        )}
                                                    </Button>
                                                )}
                                            </AlertDialogFooter>
                                        </AlertDialogContent>
                                    </AlertDialog>
                                </div>
                            </div>

                            {localAgent && (
                                <div className="w-2/3 p-6">
                                    <div className="flex items-center justify-between mb-6">
                                        <div className="flex items-center space-x-6">
                                            <RandomAvatar
                                                className="h-24 w-24 rounded-full"
                                                name={`${localAgent.name}`}
                                            />
                                            <h1 className="text-3xl font-bold">{`${localAgent.name}`}</h1>
                                        </div>
                                    </div>
                                    <div className="space-y-6">
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">名字</label>
                                            <Input
                                                name="name"
                                                value={localAgent.name}
                                                onChange={handleInputChange}
                                                placeholder="Agent Name"
                                                className={`w-full ${errors[localAgent.id]?.name ? 'border-red-500' : ''}`}
                                            />
                                            {errors[localAgent.id]?.name && <p className="text-red-500 text-sm mt-1">{errors[localAgent.id]?.name}</p>}
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">用户资料</label>
                                            <AutoResizeTextarea
                                                name="user_profile"
                                                value={localAgent.user_profile || ''}
                                                onChange={handleInputChange}
                                                placeholder="User Profile"
                                                className="w-full min-h-[80px]"
                                            />
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">风格</label>
                                            <Input
                                                name="style"
                                                value={localAgent.style || ''}
                                                onChange={handleInputChange}
                                                placeholder="Style"
                                                className="w-full"
                                            />
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">初始指令</label>
                                            <AutoResizeTextarea
                                                name="initial_instruction"
                                                value={localAgent.initial_instruction || ''}
                                                onChange={handleInputChange}
                                                placeholder="Initial Instruction"
                                                className="w-full min-h-[80px]"
                                            />
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">角色提示</label>
                                            <AutoResizeTextarea
                                                name="role_prompt"
                                                value={localAgent.role_prompt || ''}
                                                onChange={handleInputChange}
                                                placeholder="Role Prompt"
                                                className="w-full min-h-[80px]"
                                            />
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">Properties</label>
                                            <AutoResizeTextarea
                                                name="properties"
                                                value={localAgent.properties ? JSON.stringify(localAgent.properties, null, 2) : "{}"}
                                                onChange={(e) => {
                                                    if (localAgent) {
                                                        try {
                                                            const newProperties = JSON.parse(e.target.value);
                                                            const updatedAgent = { ...localAgent, properties: newProperties };
                                                            setLocalAgent(updatedAgent);

                                                            setAgents(prevAgents =>
                                                                prevAgents.map(agent =>
                                                                    agent.id === updatedAgent.id ? updatedAgent : agent
                                                                )
                                                            );

                                                            updateContextPersonas(agents.map(agent =>
                                                                agent.id === updatedAgent.id ? updatedAgent : agent
                                                            ));
                                                        } catch (error) {
                                                            console.error("Invalid JSON for properties:", error);
                                                        }
                                                    }
                                                }}
                                                placeholder="Agent Properties (JSON)"
                                                className="w-full min-h-[120px] font-mono"
                                            />
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    </CardContent>
                </Card>
                <BottomNav prevLink='/events' nextLink='/llmconfig' currStep={2} disabled={isNextDisabled} className='my-8' />
            </div>
        </div>
    )
}

export default AgentsPage;
