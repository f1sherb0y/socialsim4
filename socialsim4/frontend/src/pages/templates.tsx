import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Navbar } from '@/components/Navbar';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from "@/components/ui/alert-dialog";
import { Trash2 } from 'lucide-react';
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

import start1 from '@/assets/template2.png';
import chat from '@/assets/chat.png';
import hk5 from '@/assets/555.png';

import { BottomNav } from '@/components/BottomNav';
import { useSimContext } from '@/SimContext';
import { apis } from '@/lib/api';
import DescriptionCard from '@/components/DescriptionCard';
import backgroundImage from '@/assets/Untitled.png';

const getTemplateImage = (template: apis.DBTemplate) => {
    if (template.name.includes('Simple Chat')) {
        return chat;
    } else if (template.name.includes('Virtual Village')) {
        return start1;
    } else if (template.name.includes('Town Council')) {
        return hk5;
    }
    return chat;
};

export const TemplatePage = () => {
    const ctx = useSimContext();

    const [selectedTemplate, setSelectedTemplate] = useState<number | null>(null);
    const [templates, setTemplates] = useState<apis.DBTemplate[]>([]);
    const [publicTemplates, setPublicTemplates] = useState<apis.DBTemplate[]>([]);
    const [userTemplates, setUserTemplates] = useState<apis.DBTemplate[]>([]);

    useEffect(() => {
        const fetchTemplates = async () => {
            try {
                const response = await apis.fetchTemplates();
                const allTemplates = response.public_templates; // The new API returns a single list
                setTemplates(allTemplates);

                // Filter templates into public and user-owned
                const publicTmpls = allTemplates.filter(t => t.is_public);
                const userTmpls = allTemplates.filter(t => !t.is_public);
                setPublicTemplates(publicTmpls);
                setUserTemplates(userTmpls);

                ctx.setData({
                    ...ctx.data,
                    allTemplates: allTemplates,
                    allEnvs: allTemplates.map(t => t.name)
                });
            } catch (err) {
                console.error("Failed to fetch templates:", err);
                // Handle error, maybe show a toast message
            }
        };

        fetchTemplates();

        if (ctx.data.templateId) {
            setSelectedTemplate(ctx.data.templateId);
        }
    }, []);

    const handleSelectTemplate = (templateId: number) => {
        const updatedData = {
            ...ctx.data,
            currentTemplate: undefined,
            templateId: templateId
        };
        ctx.setData(updatedData);
        setSelectedTemplate(templateId);
    };

    const handleDeleteTemplate = async (templateId: number) => {
        try {
            await apis.deleteTemplate(templateId);
            const updatedTemplates = templates.filter(t => t.id !== templateId);
            setTemplates(updatedTemplates);

            const publicTmpls = updatedTemplates.filter(t => t.is_public);
            const userTmpls = updatedTemplates.filter(t => !t.is_public);
            setPublicTemplates(publicTmpls);
            setUserTemplates(userTmpls);

            ctx.setData({
                ...ctx.data,
                allTemplates: updatedTemplates,
                allEnvs: updatedTemplates.map(t => t.name)
            });

            if (selectedTemplate === templateId) {
                setSelectedTemplate(null);
                ctx.setData({
                    ...ctx.data,
                    templateId: undefined,
                    currentTemplate: undefined
                });
            }
        } catch (err) {
            console.error("Failed to delete template:", err);
            alert("Failed to delete template");
        }
    };

    return (
        <div className="flex flex-col bg-gray-100 min-h-screen" style={{ backgroundImage: `url(${backgroundImage})`, backgroundSize: '100% 100%', backgroundRepeat: 'no-repeat', backgroundAttachment: 'fixed' }}>
            <Navbar className="border-white border-b-[1px] border-opacity-40 bg-white bg-opacity-40 backdrop-filter backdrop-blur-lg dark:border-b-slate-700 dark:bg-background" />
            <main className="container flex-grow mx-auto">

                <h2 className="text-5xl font-bold my-12 text-left text-black-800"><span className="font-mono">Step 1.</span>选择仿真模板</h2>

                <DescriptionCard
                    title="什么是仿真模板？"
                    description="仿真模板是预先配置好的社会情境和参数集合，集成了大型语言模型（LLM）技术。每个模板都代表一个独特的社交场景，如公共事件讨论、市长竞选或社区互动。这些模板预设了智能体数量、环境特征和互动规则，让您可以快速开始探索复杂的社会动态。选择一个模板，即可启动一个由AI驱动的、高度逼真的社会仿真实验。"
                />

                {publicTemplates.length > 0 && (
                    <>
                        <h3 className="text-3xl font-bold my-8 text-left text-black-800">公共模板</h3>
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8 mb-12">
                            {publicTemplates.map((template) => (
                                <Card
                                    key={template.id}
                                    className={`w-full rounded-xl bg-opacity-30 bg-white overflow-hidden shadow-lg hover:shadow-2xl transition-all duration-150 cursor-pointer ${selectedTemplate === template.id ? 'ring-4 ring-indigo-600 ring-offset-4' : ''}`}
                                    onClick={() => handleSelectTemplate(template.id)}
                                >
                                    <img
                                        src={getTemplateImage(template)}
                                        alt={template.name}
                                        className="w-full h-48 object-cover"
                                    />
                                    <CardHeader className="p-4 bg-gradient-to-r from-purple-600 to-blue-500">
                                        <CardTitle className="text-xl font-semibold text-white">{template.name}</CardTitle>
                                    </CardHeader>
                                    <CardContent className="p-4">
                                        <p className="text-sm text-gray-600">{template.description}</p>
                                    </CardContent>
                                </Card>
                            ))}
                        </div>
                    </>
                )}

                {userTemplates.length > 0 && (
                    <>
                        <h3 className="text-3xl font-bold my-8 text-left text-black-800">您创建的模板</h3>
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8 mb-12">
                            {userTemplates.map((template) => (
                                <Card
                                    key={template.id}
                                    className={`w-full relative rounded-xl bg-opacity-30 bg-white overflow-hidden shadow-lg hover:shadow-2xl transition-all duration-150 cursor-pointer ${selectedTemplate === template.id ? 'ring-4 ring-indigo-600 ring-offset-4' : ''}`}
                                    onClick={() => handleSelectTemplate(template.id)}
                                >
                                    <div className="absolute top-2 right-2">
                                        <AlertDialog>
                                            <AlertDialogTrigger asChild>
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    className="bg-red-500 hover:bg-red-600 text-white p-1 rounded-full w-8 h-8 flex items-center justify-center"
                                                    onClick={(e) => e.stopPropagation()}
                                                >
                                                    <Trash2 className="h-4 w-4" />
                                                </Button>
                                            </AlertDialogTrigger>
                                            <AlertDialogContent>
                                                <AlertDialogHeader>
                                                    <AlertDialogTitle>您确定要删除这个模板吗？</AlertDialogTitle>
                                                    <AlertDialogDescription>
                                                        该操作无法撤销。模板 "{template.name}" 将从服务器上永久删除。
                                                    </AlertDialogDescription>
                                                </AlertDialogHeader>
                                                <AlertDialogFooter>
                                                    <AlertDialogCancel>取消</AlertDialogCancel>
                                                    <AlertDialogAction
                                                        onClick={(e) => {
                                                            e.stopPropagation();
                                                            handleDeleteTemplate(template.id);
                                                        }}
                                                        className="bg-red-600 hover:bg-red-700"
                                                    >
                                                        删除
                                                    </AlertDialogAction>
                                                </AlertDialogFooter>
                                            </AlertDialogContent>
                                        </AlertDialog>
                                    </div>
                                    <img
                                        src={getTemplateImage(template)}
                                        alt={template.name}
                                        className="w-full h-48 object-cover"
                                    />
                                    <CardHeader className="p-4 bg-gradient-to-r from-purple-600 to-blue-500">
                                        <CardTitle className="text-xl font-semibold text-white">{template.name}</CardTitle>
                                    </CardHeader>
                                    <CardContent className="p-4">
                                        <p className="text-sm text-gray-600">{template.description}</p>
                                    </CardContent>
                                </Card>
                            ))}
                        </div>
                    </>
                )}
                <BottomNav
                    prevLink='/welcome'
                    nextLink='/events'
                    currStep={0}
                    disabled={!selectedTemplate}
                    className='my-8'
                />
            </main>
        </div>
    );
};
