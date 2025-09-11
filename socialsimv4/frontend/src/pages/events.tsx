import { useEffect, useState } from 'react';
import { Navbar } from "@/components/Navbar";
import { BottomNav } from "@/components/BottomNav";
import { Card, CardContent, } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useSimContext } from '@/SimContext';
import { apis } from '@/lib/api';
import { AutoResizeTextarea } from '@/components/autoResizeTextArea';
import { FlowchartCanvas } from "@/components/FlowchartCanvas";

import { Plus, InfoIcon, Trash2 } from "lucide-react";
import DescriptionCard from '@/components/DescriptionCard';

import backgroundImage from '@/assets/Untitled.png'

export interface Event {
    name: string;
    policy: string;
    websearch: string;
    description: string;
}

export const EventsPage = () => {
    const ctx = useSimContext();

    const [experimentName, setExperimentName] = useState(ctx.data.currSimCode || '');
    const [replicateCount, setReplicateCount] = useState(ctx.data.initialRounds?.toString() || '');
    const [events, setEvents] = useState<(Event & { id: number })[] | undefined>(
        ctx.data.currentTemplate?.events.map((event, index) => ({
            ...event,
            id: index + 1,
            name: event.description ? event.description.slice(0, 28) : `事件 ${index + 1}`
        }))
    );

    const [selectedEvent, setSelectedEvent] = useState<(Event & { id: number }) | null>(null);
    const [nextEventId, setNextEventId] = useState(1);
    const [eventDescriptionError, setEventDescriptionError] = useState('');
    const workflow = {
            "plan": {
                task: "",
                output_format: {
                    "reasoning": "",
                    "decision": ""
                }
            },
            "execute": {
                task: "",
                output_format: {
                    "reasoning": "",
                    "decision": ""
                }
            }
        };

    useEffect(() => {
        if (events && events.length > 0) {
            setNextEventId(Math.max(...events.map(e => e.id)) + 1);
        } else {
            setNextEventId(1);
        }
    }, [events]);

    useEffect(() => {
        if (events && events.length > 0 && !selectedEvent) {
            setSelectedEvent(events[0]);
        }
    }, [events]);




    const [errors, setErrors] = useState({
        experimentName: '',
        replicateCount: '',
    });

    useEffect(() => {
        const validateFields = () => {
            let newErrors = {
                experimentName: '',
                replicateCount: '',
            };

            if (experimentName.trim() === '') {
                newErrors.experimentName = '实验名称不能为空';
            } else if (ctx.data.allTemplates?.map(t => t.name).includes(experimentName)) {
                newErrors.experimentName = '实验名称已存在';
            } else if (ctx.data.allEnvs.includes(experimentName)) {
                newErrors.experimentName = '实验名称已存在';
            }

            const numValue = parseInt(replicateCount, 10);
            if (replicateCount.trim() === '') {
                newErrors.replicateCount = '初始仿真轮数不能为空';
            } else if (isNaN(numValue) || numValue < 0) {
                newErrors.replicateCount = '请输入有效的非负整数';
            }

            setErrors(newErrors);
        };

        validateFields();
    }, [experimentName, replicateCount, ctx.data.allTemplates]);

    const updateExperimentName = (value: string) => {
        setExperimentName(value);
        ctx.setData({
            ...ctx.data,
            currSimCode: value
        });
    };

    const updateWorkflow = (value: Record<string, apis.Stage>) => {
        // setWorkflow(value);
        ctx.setData({
            ...ctx.data,
            currentTemplate: ctx.data.currentTemplate ? {
                ...ctx.data.currentTemplate,
                workflow: value
            } : undefined
        })
    }

    const updateReplicateCount = (value: string) => {
        setReplicateCount(value);
        const numValue = parseInt(value, 10);
        if (!isNaN(numValue) && numValue >= 0) {
            ctx.setData({
                ...ctx.data,
                initialRounds: numValue
            });
        } else {
            ctx.setData({
                ...ctx.data,
                initialRounds: undefined
            });
        }
    };

    const isFormValid = () => {
        const numValue = parseInt(replicateCount, 10);
        return experimentName.trim() !== '' &&
            !isNaN(numValue) &&
            numValue >= 0 &&
            !ctx.data.allEnvs.includes(experimentName);
    };

    const addNewEvent = () => {
        const newEvent: Event & { id: number } = {
            id: nextEventId,
            name: `事件 ${nextEventId}`,
            policy: '',
            websearch: '',
            description: '',
        };
        setEvents([...events || [], newEvent]);
        setNextEventId(nextEventId + 1);
        setSelectedEvent(newEvent);
        setEventDescriptionError('事件描述不能为空');
        ctx.setData({
            ...ctx.data,
            currentTemplate: ctx.data.currentTemplate ? {
                ...ctx.data.currentTemplate,
                events: [...events || [], newEvent]
            } : undefined
        });
    };

    const removeEvent = (id: number) => {
        setEvents(events?.filter(event => event.id !== id));
        ctx.setData({
            ...ctx.data,
            currentTemplate: ctx.data.currentTemplate ? {
                ...ctx.data.currentTemplate,
                events: ctx.data.currentTemplate?.events.filter((_, index) => index + 1 !== id) || []
            } : undefined
        });
        if (selectedEvent && selectedEvent.id === id) {
            setSelectedEvent(null);
        }
    };

    const updateEvent = (field: keyof Event, value: string) => {
        if (selectedEvent) {
            const updatedEvent = { ...selectedEvent, [field]: value };

            // 当description更新时,同步更新name
            if (field === 'description') {
                updatedEvent.name = value ? value.slice(0, 10) : `事件 ${selectedEvent.id}`;
            }

            setSelectedEvent(updatedEvent);
            setEvents(events?.map(e => e.id === selectedEvent.id ? updatedEvent : e));

            if (field === 'description') {
                if (value.trim() === '') {
                    setEventDescriptionError('事件描述不能为空');
                } else {
                    setEventDescriptionError('');
                }
            }

            ctx.setData({
                ...ctx.data,
                currentTemplate: ctx.data.currentTemplate ? {
                    ...ctx.data.currentTemplate,
                    events: events?.map((e, index) => index + 1 === selectedEvent.id ? updatedEvent : e) || []
                } : undefined
            });
        }
    };

    useEffect(() => {
        const fetchTemplates = async () => {
            try {
                if (ctx.data.templateId && !ctx.data.currentTemplate) {
                    const templateData = await apis.fetchTemplate(ctx.data.templateId);
                    const events = templateData.events.map((value, index) => ({
                        ...value,
                        id: index + 1,
                        name: value.description ? value.description.slice(0, 28) : `事件 ${index + 1}`
                    }));
                    ctx.setData({
                        ...ctx.data,
                        currentTemplate: {
                            ...templateData,
                            events: events,
                            workflow: templateData.workflow
                        }
                    });
                    setEvents(events);
                }
            } catch (err) {
                console.error("Failed to fetch template detail:", err);
            }
        }

        fetchTemplates();
    }, []);

    return (
        <div className="flex flex-col min-h-screen bg-gray-100" style={{ backgroundImage: `url(${backgroundImage})`, backgroundSize: '100% 100%', backgroundRepeat: 'no-repeat', backgroundAttachment: 'fixed' }}>
            <Navbar className="border-white border-b-[1px] border-opacity-40 bg-white bg-opacity-40 backdrop-filter backdrop-blur-lg dark:border-b-slate-700 dark:bg-background" />
            <div className="container mx-auto">
                <h2 className="text-5xl font-bold my-12 text-left text-black-800"><span className="font-mono">Step 2.</span>方案设计</h2>
                <DescriptionCard
                    title="设计仿真方案"
                    description="定义和配置社会仿真实验的核心要素。首先，设置实验名称和初次仿真轮数，即初次进入实验之后自动运行的仿真轮数。然后，添加和编辑仿真中的事件，每个事件代表一个特定的社会情境或讨论话题。您可以为每个事件提供详细描述、相关政策和网络搜索关键词。这些事件将成为智能体互动和讨论的焦点，从而塑造整个仿真过程。通过精心设计这些元素，您可以创建一个丰富、多样的仿真环境，以探索复杂的社会动态。"
                />


                <Card className="bg-opacity-70 bg-white">
                    <CardContent className='pt-8'>
                        <div className="grid md:grid-cols-2 gap-8 flex-col">
                            {/* Left Column - Experiment Settings */}

                            <div className="space-y-6 flex flex-col h-full">
                                <h3 className="text-lg font-semibold text-gray-700 mb-3">基本信息</h3>
                                <div className='grid grid-cols-2 gap-4'>
                                    <div>
                                        <label htmlFor="experimentName" className="block text-sm font-medium text-gray-700 mb-1">实验名称</label>
                                        <Input
                                            id="experimentName"
                                            value={experimentName}
                                            onChange={(e) => updateExperimentName(e.target.value)}
                                            placeholder="请输入实验名称"
                                            className={`w-full ${errors.experimentName ? 'border-red-500' : ''}`}
                                        />
                                        {errors.experimentName && <p className="text-red-500 text-xs mt-1">{errors.experimentName}</p>}
                                    </div>

                                    <div>
                                        <label htmlFor="replicateCount" className="block text-sm font-medium text-gray-700 mb-1">初始仿真轮数</label>
                                        <div className="flex items-center">
                                            <Input
                                                id="replicateCount"
                                                type="number"
                                                min="1"
                                                step="1"
                                                value={replicateCount}
                                                onChange={(e) => updateReplicateCount(e.target.value)}
                                                placeholder="请输入仿真轮数"
                                                className={`mr-2 ${errors.replicateCount ? 'border-red-500' : ''}`}
                                            />
                                            <span className="text-gray-600">轮</span>
                                        </div>
                                        {errors.replicateCount && <p className="text-red-500 text-xs mt-1">{errors.replicateCount}</p>}
                                    </div>
                                </div>

                                {/* Flowchart Canvas */}
                                <div className="flex flex-col flex-grow flex" >
                                    <h3 className="text-lg font-semibold text-gray-700 mb-3">流程设计</h3>
                                    <FlowchartCanvas
                                        workflow={workflow}
                                        onUpdate={updateWorkflow}
                                    />
                                </div>
                            </div>



                            {/* Right Column - Event Selection and Details */}
                            <div className="space-y-6">
                                {/* Event Selection Dropdown */}
                                <div>
                                    <h3 className="text-lg font-semibold text-gray-700 mb-3">事件列表</h3>

                                    <div className="bg-blue-50 border-l-4 border-blue-400 p-4 mb-4 rounded-r-lg">
                                        <div className="flex">
                                            <div className="flex-shrink-0">
                                                <InfoIcon className="h-5 w-5 text-blue-400" aria-hidden="true" />
                                            </div>
                                            <div className="ml-3">
                                                <p className="text-sm text-blue-700">
                                                    事件是仿真中的讨论话题。每个事件代表一个特定的社会情境或议题，智能体将围绕这些事件展开互动和讨论。
                                                </p>
                                            </div>
                                        </div>
                                    </div>

                                    {/* Dropdown and Add Button Row */}
                                    <div className="flex items-center gap-2">
                                        <Select
                                            value={selectedEvent ? selectedEvent.id.toString() : ""}
                                            onValueChange={(value) => {
                                                const event = events?.find(e => e.id.toString() === value);
                                                if (event) setSelectedEvent(event);
                                            }}
                                        >
                                            <SelectTrigger className="flex-1">
                                                <SelectValue placeholder="选择事件" />
                                            </SelectTrigger>
                                            <SelectContent>
                                                {events?.map((event) => (
                                                    <SelectItem
                                                        key={event.id}
                                                        value={event.id.toString()}
                                                        className={event.description.trim() === '' ? 'text-red-500' : ''}
                                                    >
                                                        {event.name}
                                                    </SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>

                                        <div className="flex gap-2">
                                            <Button
                                                variant="outline"
                                                className="text-red-600 hover:bg-red-50"
                                                onClick={() => selectedEvent && removeEvent(selectedEvent.id)}
                                                disabled={!selectedEvent}
                                            >
                                                <Trash2 className="h-4 w-4 mr-2" /> 删除
                                            </Button>
                                            <Button
                                                variant="outline"
                                                className="text-blue-600 hover:bg-blue-50"
                                                onClick={addNewEvent}
                                            >
                                                <Plus className="h-4 w-4 mr-2" /> 添加新事件
                                            </Button>
                                        </div>
                                    </div>
                                </div>

                                {/* Event Details Section */}
                                <div className="bg-indigo-50 p-6 rounded-lg">
                                    <h3 className="text-lg font-semibold text-gray-700 mb-4">事件详情</h3>
                                    {selectedEvent ? (
                                        <div className="space-y-4">
                                            <div>
                                                <label htmlFor="eventDescription" className="block text-sm font-medium text-gray-700 mb-1">事件描述</label>
                                                <AutoResizeTextarea
                                                    id="eventDescription"
                                                    value={selectedEvent.description}
                                                    onChange={(e) => updateEvent('description', e.target.value)}
                                                    placeholder="请输入事件描述"
                                                    rows={3}
                                                    className={selectedEvent.description == '' ? 'border-red-500' : ''}
                                                />
                                                {selectedEvent.description == '' && <p className="text-red-500 text-xs mt-1">{eventDescriptionError}</p>}
                                            </div>
                                            <div>
                                                <label htmlFor="eventName" className="block text-sm font-medium text-gray-700 mb-1">事件名称</label>
                                                <Input
                                                    id="eventName"
                                                    value={selectedEvent.name}
                                                    onChange={(e) => updateEvent('name', e.target.value)}
                                                    placeholder="请输入事件名称"
                                                />
                                            </div>
                                            <div>
                                                <label htmlFor="eventPolicy" className="block text-sm font-medium text-gray-700 mb-1">事件政策</label>
                                                <AutoResizeTextarea
                                                    id="eventPolicy"
                                                    value={selectedEvent.policy}
                                                    onChange={(e) => updateEvent('policy', e.target.value)}
                                                    placeholder="请输入事件政策"
                                                    rows={3}
                                                />
                                            </div>
                                            <div>
                                                <label htmlFor="eventWebsearch" className="block text-sm font-medium text-gray-700 mb-1">网络搜索</label>
                                                <AutoResizeTextarea
                                                    id="eventWebsearch"
                                                    value={selectedEvent.websearch}
                                                    onChange={(e) => updateEvent('websearch', e.target.value)}
                                                    placeholder="请输入事件政策"
                                                    rows={3}
                                                />
                                            </div>
                                        </div>
                                    ) : (
                                        <p className="text-gray-500 text-center">请选择一个事件来查看和编辑详情</p>
                                    )}
                                </div>
                            </div>
                        </div>
                    </CardContent>
                </Card>
                <BottomNav
                    prevLink='/templates'
                    nextLink='/agents'
                    currStep={1}
                    disabled={!isFormValid()}
                    className='my-8'
                />
            </div>
        </div>
    );
}
