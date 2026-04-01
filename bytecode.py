import dis
import types
import io
from typing import List, Dict, Any

class BytecodeGenerator:
    def __init__(self):
        self.bytecode = []
    
    def generate(self, code: str) -> List[Dict[str, Any]]:
        """Generate bytecode from Python code"""
        try:
            # Compile the code
            compiled_code = compile(code, '<string>', 'exec')
            
            # Disassemble the bytecode
            self.bytecode = []
            self._disassemble(compiled_code)
            
            return self.bytecode
        except SyntaxError as e:
            return [{
                'error': f'Syntax error: {str(e)}',
                'line': e.lineno,
                'column': e.offset
            }]
        except Exception as e:
            return [{
                'error': f'Bytecode generation error: {str(e)}'
            }]
    
    def _disassemble(self, code_obj: types.CodeType, offset: int = 0):
        """Disassemble a code object recursively"""
        # Get bytecode instructions
        instructions = list(dis.get_instructions(code_obj))
        
        for i, instr in enumerate(instructions):
            instruction_info = {
                'offset': instr.offset + offset,
                'opcode': instr.opcode,
                'opname': instr.opname,
                'arg': instr.arg,
                'argval': instr.argval,
                'argrepr': instr.argrepr,
                'line': instr.lineno,
                'starts_line': instr.starts_line,
                'is_jump_target': instr.is_jump_target,
                'positions': instr.positions if hasattr(instr, 'positions') else None
            }
            
            self.bytecode.append(instruction_info)
        
        # Handle nested code objects (functions, lambdas, etc.)
        for const in code_obj.co_consts:
            if isinstance(const, types.CodeType):
                self._disassemble(const, offset)
    
    def get_bytecode_summary(self, code: str) -> Dict[str, Any]:
        """Get a summary of bytecode information"""
        try:
            compiled_code = compile(code, '<string>', 'exec')
            
            summary = {
                'code_info': {
                    'argcount': compiled_code.co_argcount,
                    'nlocals': compiled_code.co_nlocals,
                    'stacksize': compiled_code.co_stacksize,
                    'flags': compiled_code.co_flags,
                    'code_length': len(compiled_code.co_code),
                    'consts_count': len(compiled_code.co_consts),
                    'names_count': len(compiled_code.co_names),
                    'varnames_count': len(compiled_code.co_varnames),
                    'cellvars_count': len(compiled_code.co_cellvars),
                    'freevars_count': len(compiled_code.co_freevars),
                    'filename': compiled_code.co_filename,
                    'name': compiled_code.co_name,
                    'firstlineno': compiled_code.co_firstlineno,
                    'lnotab': compiled_code.co_lnotab if hasattr(compiled_code, 'co_lnotab') else None
                },
                'constants': list(compiled_code.co_consts),
                'names': list(compiled_code.co_names),
                'varnames': list(compiled_code.co_varnames),
                'cellvars': list(compiled_code.co_cellvars),
                'freevars': list(compiled_code.co_freevars)
            }
            
            return summary
            
        except SyntaxError as e:
            return {
                'error': f'Syntax error: {str(e)}',
                'line': e.lineno
            }
    
    def get_opcode_info(self) -> List[Dict[str, Any]]:
        """Get information about all opcodes"""
        opcode_info = []
        
        for name in dis.opmap:
            opcode = dis.opmap[name]
            info = {
                'name': name,
                'opcode': opcode,
                'description': dis.opname[opcode] if opcode < len(dis.opname) else 'UNKNOWN'
            }
            
            # Add additional information for specific opcodes
            if hasattr(dis, 'hasconst') and opcode in dis.hasconst:
                info['type'] = 'const'
            elif hasattr(dis, 'hasname') and opcode in dis.hasname:
                info['type'] = 'name'
            elif hasattr(dis, 'hasjrel') and opcode in dis.hasjrel:
                info['type'] = 'jump_relative'
            elif hasattr(dis, 'hasjabs') and opcode in dis.hasjabs:
                info['type'] = 'jump_absolute'
            elif hasattr(dis, 'haslocal') and opcode in dis.haslocal:
                info['type'] = 'local'
            elif hasattr(dis, 'hascompare') and opcode in dis.hascompare:
                info['type'] = 'compare'
            elif hasattr(dis, 'hasfree') and opcode in dis.hasfree:
                info['type'] = 'free'
            else:
                info['type'] = 'other'
            
            opcode_info.append(info)
        
        return sorted(opcode_info, key=lambda x: x['opcode'])
    
    def format_bytecode(self, bytecode_instructions: List[Dict[str, Any]]) -> str:
        """Format bytecode instructions for display"""
        output = []
        
        for instr in bytecode_instructions:
            if 'error' in instr:
                output.append(f"Error: {instr['error']}")
                continue
            
            # Format the instruction
            line_parts = []
            
            # Offset
            offset_str = f"{instr['offset']:4d}"
            line_parts.append(offset_str)
            
            # Jump target indicator
            if instr['is_jump_target']:
                line_parts.append('>>')
            else:
                line_parts.append('  ')
            
            # Opcode and argument
            if instr['arg'] is not None:
                line_parts.append(f"{instr['opname']:20} {instr['arg']:3d}")
            else:
                line_parts.append(f"{instr['opname']:23}")
            
            # Argument representation
            if instr['argrepr']:
                line_parts.append(f"({instr['argrepr']})")
            
            # Line number
            if instr['line'] is not None:
                line_parts.append(f"#{instr['line']:4d}")
            
            output.append(' '.join(line_parts))
        
        return '\n'.join(output)
    
    def analyze_stack_effect(self, code: str) -> Dict[str, Any]:
        """Analyze stack effects of bytecode instructions"""
        try:
            compiled_code = compile(code, '<string>', 'exec')
            instructions = list(dis.get_instructions(compiled_code))
            
            stack_analysis = []
            stack_depth = 0
            max_stack_depth = 0
            
            for instr in instructions:
                # Get stack effect for this instruction
                try:
                    effect = dis.stack_effect(instr.opcode, instr.arg)
                except:
                    effect = 0
                
                stack_depth += effect
                max_stack_depth = max(max_stack_depth, stack_depth)
                
                stack_analysis.append({
                    'offset': instr.offset,
                    'opname': instr.opname,
                    'stack_effect': effect,
                    'stack_depth_before': stack_depth - effect,
                    'stack_depth_after': stack_depth
                })
            
            return {
                'instructions': stack_analysis,
                'max_stack_depth': max_stack_depth,
                'final_stack_depth': stack_depth
            }
            
        except Exception as e:
            return {
                'error': f'Stack analysis error: {str(e)}'
            }
