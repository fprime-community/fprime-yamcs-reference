module ComCcsdsConfig {
    #Base ID for the ComCcsds Subtopology, all components are offsets from this base ID
    constant BASE_ID = 0x02000000
    
    module QueueSizes {
        constant comQueue    = 50
        constant aggregator  = 10
    }
    
    module StackSizes {
        constant comQueue   = 64 * 1024
        constant aggregator = 64 * 1024
    }

    module Priorities {
        constant aggregator = 30
        constant comQueue   = 29
    }

    module CpuAffinities {
        constant aggregator = Os.TASK_DEFAULT
        constant comQueue   = Os.TASK_DEFAULT
    }

    # Queue configuration constants
    module QueueDepths {
        constant events      = 200             
        constant tlm         = 500            
        constant file        = 100            
    }

    module QueuePriorities {
        constant events      = 0                 
        constant tlm         = 2                 
        constant file        = 1                   
    }

    # Aggregator configuration constants
    module Aggregator {
        @ Bytes of TM data field available to Svc.ComAggregator output, less the SDLS overhead inserted between
        @ the aggregator and Svc.Ccsds.TmFramer: 2-byte SA index, 12-byte AES-GCM IV, 16-byte AES-GCM tag.
        @ Svc.Ccsds.TmFramer asserts unless the SDLS output fills Svc.Ccsds.TmDataFieldSize exactly.
        constant aggregationSize = Svc.Ccsds.TmDataFieldSize - Svc.Ccsds.SdlsSaIndexSize - 28
        @ Controls whether to span packets across transfer frames (see Svc.ComAggregator).
        @ Requires Svc.Ccsds.TmFramer as the transfer frame layer (sole consumer of FrameContext.firstHeaderPointer)
        @ and a ground deframer that reassembles spanned packets using the First Header Pointer.
        @ Spanning fills the TM data field exactly, which places the SDLS AES-GCM tag where YAMCS expects it.
        constant enablePacketSpanning = true
    }

    # Buffer management constants
    module BuffMgr {
        constant frameAccumulatorSize  = 2048     
        constant commsBuffSize         = 2048      
        constant commsFileBuffSize     = 3000      
        constant commsBuffCount        = 20        
        constant commsFileBuffCount    = 30       
        constant commsBuffMgrId        = 200      
    }
}
